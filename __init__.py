#region концепция модуля
# 1. Каждая функция работает как в классе, так и отдельно
#endregion концепция модуля


import ldap3


#region отдельные функции
def get_active_directory_conn(ad_servers:[], login:str, password:str):
    """Получить соединение с Active Directory\n
    adServers - список серверов AD\n
    login - логин учётки AD для соединения\n
    password - пароль учётки AD для соединения"""

    # формирование пула AD серверов
    ad_srv_pool = ldap3.ServerPool(None)
    for srv in ad_servers:
        ad_srv_pool.add(ldap3.Server(srv))

    # соединяемся с AD
    conn = ldap3.Connection(ad_srv_pool, login, password)
    if conn.bind():
        return conn

def get_ad_objects(ldap_filter:str, attributes:[], path_dn:str, ad_conn):
    """Получить объекты по LDAP-фильтру\n
    ldapFilter - фильтр LDAP\n
    attributes - список искомых атрибутов\n
    path_dn - путь distinguishedName для поиска
    ad_conn - соединитель Active Directory"""

    ad_conn.search(path_dn, ldap_filter, attributes=attributes)
    return ad_conn.entries

def get_ad_user(user_login:str, attrs:[], path_dn:str, ad_conn):
    """Получить пользователя с необходимыми атрибутами по логину\n
    user_login - логин\n
    attrs - массив искомых атрибутов пользователя\n
    path_dn - dn путь для поиска. По умолчанию self.search_dn
    ad_conn - соединитель Active Directory"""

    ldap_filter = f'(&(objectCategory=person)(objectClass=user)(sAMAccountName={user_login}))'
    ad_conn.search(path_dn, ldap_filter, attributes=attrs)

    if len(ad_conn.entries) == 1:
        return ad_conn.entries[0]
    else:
        return None

def get_ad_group(group_login:str, attrs:[], path_dn:str, ad_conn):
    """Получить группу с необходимыми атрибутами по логину (sAMAccountName)\n
    group_login - логин группы (это атрибут sAMAccountName)\n
    attrs - массив искомых атрибутов группы\n
    path_dn - dn путь для поиска. По умолчанию self.search_dn\n
    ad_conn - соединитель Active Directory"""

    ldap_filter = f'(&(objectCategory=group)(sAMAccountName={group_login}))'
    ad_conn.search(path_dn, ldap_filter, attributes=attrs)

    if len(ad_conn.entries) == 1:
        return ad_conn.entries[0]
    else:
        return None

def add_ad_user_to_group(user_login:str, group_login:str, path_dn:str, ad_conn):
    """Добавить пользователя AD в группу AD\n
    user_login - логин пользователя\n
    group_login - логин группы\n
    path_dn - dn путь для поиска сотрудника и группы\n
    ad_conn - соединитель Active Directory"""

    user = get_ad_user(user_login, ['distinguishedName'], path_dn, ad_conn)
    group = get_ad_group(group_login, ['distinguishedName'], path_dn, ad_conn)

    if user == None:
        raise ValueError('Неверно задан логин пользователя, такого пользователя не существует')
    if group == None:
        raise ValueError('Неверно задан логин группы, такой группы не существует')

    ldap3.extend.microsoft.addMembersToGroups.ad_add_members_to_groups(
        ad_conn,
        user.distinguishedName.value,
        group.distinguishedName.value
    )

    if not check_ad_user_in_group(user_login, group_login, path_dn, ad_conn):
        raise PermissionError(f'Сотрудник "{user_login}" не добавлен в группу "{group_login}". '\
                               'Вероятно, недостаточно прав для этой операции.')

def remove_ad_user_from_group(user_login:str, group_login:str, path_dn:str, ad_conn):
    """Удалить пользователя AD из группы AD\n
    user_login - логин пользователя\n
    group_login - логин группы\n
    path_dn - dn путь для поиска сотрудника и группы\n
    ad_conn - соединитель Active Directory"""

    user = get_ad_user(user_login, ['distinguishedName'], path_dn, ad_conn)
    group = get_ad_group(group_login, ['distinguishedName'], path_dn, ad_conn)

    if user == None:
        raise ValueError('Неверно задан логин пользователя, такого пользователя не существует')
    if group == None:
        raise ValueError('Неверно задан логин группы, такой группы не существует')    

    ldap3.extend.microsoft.removeMembersFromGroups.ad_remove_members_from_groups(
        ad_conn,
        user.distinguishedName.value,
        group.distinguishedName.value,
        True
    )

    if check_ad_user_in_group(user_login, group_login, path_dn, ad_conn):
        raise PermissionError(f'Сотрудник "{user_login}" не удалён из группы "{group_login}". '\
                               'Вероятно, недостаточно прав для этой операции.')

def check_ad_user_in_group(user_login:str, group_login:str, path_dn:str, ad_conn):
    """Проверяем наличие пользователя AD в группе AD
    user_login - логин пользователя\n
    group_login - логин группы\n
    path_dn - dn путь для поиска сотрудника и группы\n
    ad_conn - соединитель Active Directory"""

    # ищем всех членов группы
    group = get_ad_group(group_login, ['distinguishedName'], path_dn, ad_conn)
    if group == None:
        raise ValueError(f'Неверно задан логин группы "{group_login}", такой группы не существует')    
    ldap_filter = f'(&(memberOf:1.2.840.113556.1.4.1941:={group.distinguishedName.value})' \
                   '(objectCategory=person)(objectClass=user))'  # все пользователи члены группы (рекурсивно)
    searched_users = get_ad_objects(ldap_filter, ['sAMAccountName'], path_dn, ad_conn)

    for user in searched_users:
        if user.sAMAccountName.value == user_login:
            return True
    return False

def modify_ad_obj_attrs(obj_dn:str, modify_attrs:dict, ad_conn):
    """Изменение атрибутов объекта AD\n
    obj_dn - путь distinguishedName для объекта\n
    modify_attrs - атрибуты для изменения {attr1: value1, attr2: value2}\n
    ad_conn - соединитель Active Directory"""

    # выводим ошибку если нет объекта с distinguishedName = obj_dn
    ldap_filter = f'(distinguishedName={obj_dn})'
    searched_obj = get_ad_objects(ldap_filter, [], obj_dn, ad_conn)
    if searched_obj == []:
        raise ValueError(f'Отсутствует объект с distinguishedName = "{obj_dn}"')

    for attr_key in modify_attrs:
        # изменение атрибута
        ad_conn.modify(
            obj_dn,
            {
                attr_key: [(ldap3.MODIFY_REPLACE, [modify_attrs[attr_key]])]
            }
        )

        #проверка изменения атрибута
        updated_attr_value = getattr(
            get_ad_objects(ldap_filter, [attr_key], obj_dn, ad_conn)[0],
            attr_key    
        ).value
        if updated_attr_value != modify_attrs[attr_key]:
            raise PermissionError(f'Атрибут "{attr_key}" не изменён. Вероятно, недостаточно прав для этой операции.')
        
def clear_ad_obj_attrs(obj_dn:str, clear_attrs:[], ad_conn):
    """Очистка атрибутов объекта AD\n
    obj_dn - путь distinguishedName для объекта\n
    clear_attrs - массив имён атрибутов для очистки\n
    ad_conn - соединитель Active Directory"""

    # выводим ошибку если нет объекта с distinguishedName = obj_dn
    ldap_filter = f'(distinguishedName={obj_dn})'
    searched_obj = get_ad_objects(ldap_filter, [], obj_dn, ad_conn)
    if searched_obj == []:
        raise ValueError(f'Отсутствует объект с distinguishedName = "{obj_dn}"')

    for attr_key in clear_attrs:
        # очистка атрибута
        ad_conn.modify(
            obj_dn,
            {
                attr_key: [(ldap3.MODIFY_DELETE, [])]
            }
        )

        # проверка очистки атрибута
        updated_attr_value = getattr(
            get_ad_objects(ldap_filter, [attr_key], obj_dn, ad_conn)[0],
            attr_key    
        ).value
        if updated_attr_value != None:
            raise PermissionError(f'Атрибут "{attr_key}" не очищен. Вероятно, недостаточно прав для этой операции.')

def convert_uac_to_dict(uac_value:int):
    """Перевести значение userAccountControl в словарь\n
    uac_value - 10-ричное значение userAccountControl"""
    # переводим число в 2-ричную систему, усекая '0b', и создаём массив знаков
    # в обратном порядке
    lst_num = (list((bin(uac_value))[2:]))
    lst_num.reverse()

    # генерим словарь
    uac_attr = 1
    uac_dict = {}
    for i in lst_num:
        if i == '1':
            uac_dict.update({uac_attr: True})
        else:
            uac_dict.update({uac_attr: False})
        uac_attr *= 2

    return uac_dict

def get_uac_attr(uac_value:int, attr:int):
    """Получить булево значение любого атрибута userAccountControl\n
    uacValue - 10-ричное значение userAccountControl\n
    attr - 10-тичное значение искомого атрибута\n
    Все значения атрибутов тут:\n
    https://support.microsoft.com/ru-ru/help/305144"""

    # определение корректности требуемого атрибута
    correct_attr = [2 ** i for i in range(25)]
    if attr not in correct_attr:
        raise Exception('Некорректное 10-ричное значение атрибута userAccountControl')

    uac_dict = convert_uac_to_dict(uac_value)

    if attr in uac_dict.keys():
        return uac_dict[attr]
    else:
        return False
#endregion отдельные функции


#region класс ActiveDirectory
class ActiveDirectory:

    def __init__(self, ad_servers:[], login:str, password:str, search_dn:str):
        """Самописный модуль для удобства работы с Active Directory\n
        ad_servers - массив адресов серверов AD\n
        login - логин для подключения\n
        password - пароль для подключения\n
        search_dn - dn путь по умолчанию"""

        self.conn = get_active_directory_conn(ad_servers, login, password)
        self.search_dn = search_dn

    def get_ad_objects(self, ldap_filter:str, attributes:[], path_dn:str=None):
        """Получить AD объекты по LDAP-фильтру\n
        ldapFilter - фильтр LDAP\n
        attributes - список искомых атрибутов\n
        path_dn - путь distinguishedName для поиска"""

        # __init__
        if path_dn is None:
            path_dn = self.search_dn

        search_objects = get_ad_objects(ldap_filter, attributes, path_dn, self.conn)
        return search_objects

    def get_ad_user(self, user_login:str, attrs:[], path_dn:str=None):
        """Получить пользователя с необходимыми атрибутами по логину\n
        user_login - логин\n
        attrs - массив искомых атрибутов пользователя\n
        path_dn - dn путь для поиска. По умолчанию self.search_dn"""
        
        # __init__
        if path_dn is None:
            path_dn = self.search_dn
        
        searched_user = get_ad_user(user_login, attrs, path_dn, self.conn)
        return searched_user

    def get_ad_group(self, group_login:str, attrs:[], path_dn:str=None):
        """Получить группу с необходимыми атрибутами по логину (sAMAccountName)\n
        group_login - логин группы (это атрибут sAMAccountName)\n
        attrs - массив искомых атрибутов группы\n
        path_dn - dn путь для поиска. По умолчанию self.search_dn"""

        # __init__
        if path_dn is None:
            path_dn = self.search_dn
        
        searched_group = get_ad_group(group_login, attrs, path_dn, self.conn)
        return searched_group

    def add_ad_user_to_group(self, user_login:str, group_login:str, path_dn:str=None):
        """Добавить пользователя AD в группу AD\n
        user_login - логин пользователя\n
        group_login - логин группы\n
        path_dn - dn путь для поиска сотрудника и группы. По умолчанию self.search_dn\n"""

        # __init__
        if path_dn is None:
            path_dn = self.search_dn

        add_ad_user_to_group(user_login, group_login, path_dn, self.conn)

    def remove_ad_user_from_group(self, user_login:str, group_login:str, path_dn:str=None):
        """Удалить пользователя AD из группы AD\n
        user_login - логин пользователя\n
        group_login - логин группы\n
        path_dn - dn путь для поиска сотрудника и группы\n"""

        # __init__
        if path_dn is None:
            path_dn = self.search_dn

        remove_ad_user_from_group(user_login, group_login, path_dn, self.conn)

    def check_ad_user_in_group(self, user_login:str, group_login:str, path_dn:str=None):
        """Проверяем наличие пользователя AD в группе AD
        user_login - логин пользователя\n
        group_login - логин группы\n
        path_dn - dn путь для поиска сотрудника и группы\n"""
                
        # __init__
        if path_dn is None:
            path_dn = self.search_dn

        return check_ad_user_in_group(user_login, group_login, path_dn, self.conn)

    def modify_ad_obj_attrs(self, obj_dn:str, modify_attrs:dict):
        """Изменение атрибутов объекта AD\n
        obj_dn - путь distinguishedName для объекта\n
        modify_attrs - атрибуты для изменения {attr1: value1, attr2: value2}"""

        modify_ad_obj_attrs(obj_dn, modify_attrs, self.conn)

    def clear_ad_obj_attrs(self, obj_dn:str, clear_attrs:[]):
        """Очистка атрибутов объекта AD\n
        obj_dn - путь distinguishedName для объекта\n
        clear_attrs - массив имён атрибутов для очистки\n"""

        clear_ad_obj_attrs(obj_dn, clear_attrs, self.conn)

    @staticmethod
    def convert_uac_to_dict(uac_value:int):
        """Перевести значение userAccountControl в словарь\n
        uac_value - 10-ричное значение userAccountControl"""
        
        return convert_uac_to_dict(uac_value)
    
    @staticmethod
    def get_uac_attr(uac_value:int, attr:int):
        """Получить булево значение любого атрибута userAccountControl\n
        uacValue - 10-ричное значение userAccountControl\n
        attr - 10-тичное значение искомого атрибута\n
        Все значения атрибутов тут:\n
        https://support.microsoft.com/ru-ru/help/305144"""
        
        return get_uac_attr(uac_value, attr)
#endregion класс ActiveDirectory
