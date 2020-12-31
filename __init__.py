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

def get_ad_objects(ldap_filter:str, attributes:[], path_dn:str, ad_conn:ldap3.core.connection.Connection, error_if_empty=False):
    """Получить объекты по LDAP-фильтру\n
    ldap_filter - фильтр LDAP\n
    attributes - список искомых атрибутов\n
    path_dn - путь distinguishedName для поиска
    ad_conn - соединитель Active Directory\n
    error_if_empty - если True вызовет исключение при пустом результате"""

    ad_conn.search(path_dn, ldap_filter, attributes=attributes)
    
    if error_if_empty:
        if ad_conn.entries == []:
            raise ValueError(f'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: {ldap_filter}')
    return ad_conn.entries

def get_ad_objects_over_1000(ldap_filter:str, attributes:[], path_dn:str, ad_conn, error_if_empty=False):
    """Получить объекты по LDAP-фильтру без ограничений по их количеству
    ldap_filter - фильтр LDAP\n
    attributes - список искомых атрибутов\n
    path_dn - путь distinguishedName для поиска\n
    ad_conn - соединитель Active Directory\n
    error_if_empty - если True вызовет исключение при пустом результате"""

    # класс для возвращаемого объекта
    class LDAPObject:
        def __init__(self, obj_raw):
            self.obj_raw = obj_raw
            self.dn = obj_raw['dn']
            for attr in obj_raw['attributes']:
                setattr(
                    self,
                    attr,
                    obj_raw['attributes'][attr]
                )

    # ищем объекты и отфильтровываем системные не нужные нам объекты
    searched_objects = ad_conn.extend.standard.paged_search(path_dn, ldap_filter, attributes=attributes, generator=False)
    searched_objects_filter = filter(lambda x: x['type'] == 'searchResEntry', searched_objects)
    
    # делаем из объектов массив экземпляров нашего класса LDAPObject
    return_objs = []
    for elem in searched_objects_filter:
        return_objs.append(LDAPObject(elem))

    # возвращаем результат
    if error_if_empty:
        if return_objs == []:
            raise ValueError(f'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: {ldap_filter}')
    return return_objs

def get_ad_user(user_login:str, attrs:[], path_dn:str, ad_conn, error_if_empty=False):
    """Получить пользователя с необходимыми атрибутами по логину\n
    user_login - логин\n
    attrs - массив искомых атрибутов пользователя\n
    path_dn - dn путь для поиска\n
    ad_conn - соединитель Active Directory\n
    error_if_empty - если True вызовет исключение при пустом результате"""

    user_login = prepare_element_for_ldap_filter(user_login)
    ldap_filter = f'(&(objectCategory=person)(objectClass=user)(sAMAccountName={user_login}))'
    ad_conn.search(path_dn, ldap_filter, attributes=attrs)

    if len(ad_conn.entries) == 1:
        return ad_conn.entries[0]
    else:
        if error_if_empty:
            raise ValueError(f'Пользователь с логином "{user_login}" не найден')
        return None

def get_ad_group(group_login:str, attrs:[], path_dn:str, ad_conn, error_if_empty=False):
    """Получить группу с необходимыми атрибутами по логину (sAMAccountName)\n
    group_login - логин группы (это атрибут sAMAccountName)\n
    attrs - массив искомых атрибутов группы\n
    path_dn - dn путь для поиска\n
    ad_conn - соединитель Active Directory\n
    error_if_empty - если True вызовет исключение при пустом результате"""

    group_login = prepare_element_for_ldap_filter(group_login)
    ldap_filter = f'(&(objectCategory=group)(sAMAccountName={group_login}))'
    ad_conn.search(path_dn, ldap_filter, attributes=attrs)

    if len(ad_conn.entries) == 1:
        return ad_conn.entries[0]
    else:
        if error_if_empty:
            raise ValueError(f'Группа с логином "{group_login}" не найдена')
        return None

def add_ad_user_to_group(user_login:str, group_login:str, path_dn:str, ad_conn):
    """Добавить пользователя AD в группу AD\n
    user_login - логин пользователя\n
    group_login - логин группы\n
    path_dn - dn путь для поиска сотрудника и группы\n
    ad_conn - соединитель Active Directory"""

    user_dn = get_ad_user(user_login, ['distinguishedName'], path_dn, ad_conn, error_if_empty=True).distinguishedName.value
    group_dn = get_ad_group(group_login, ['distinguishedName'], path_dn, ad_conn, error_if_empty=True).distinguishedName.value

    ldap3.extend.microsoft.addMembersToGroups.ad_add_members_to_groups(
        ad_conn,
        user_dn,
        group_dn
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

    user_dn = get_ad_user(user_login, ['distinguishedName'], path_dn, ad_conn, error_if_empty=True).distinguishedName.value
    group_dn = get_ad_group(group_login, ['distinguishedName'], path_dn, ad_conn, error_if_empty=True).distinguishedName.value   

    ldap3.extend.microsoft.removeMembersFromGroups.ad_remove_members_from_groups(
        ad_conn,
        user_dn,
        group_dn,
        True
    )

    if check_ad_user_in_group(user_login, group_login, path_dn, ad_conn):
        raise PermissionError(f'Сотрудник "{user_login}" не удалён из группы "{group_login}". '\
                               'Вероятно, недостаточно прав для этой операции.')

def check_ad_user_in_group(user_login:str, group_login:str, path_dn:str, ad_conn, recurse=True):
    """Проверяем наличие пользователя AD в группе AD
    user_login - логин пользователя\n
    group_login - логин группы\n
    path_dn - dn путь для поиска сотрудника и группы\n
    ad_conn - соединитель Active Directory"""

    # просто чтобы вызвать ошибку, если пользователя не существует
    get_ad_user(user_login, [], path_dn, ad_conn, error_if_empty=True)

    # готовим ldap-фильтр
    group_dn = get_ad_group(group_login, ['distinguishedName'], path_dn, ad_conn, error_if_empty=True).distinguishedName.value
    group_dn = prepare_element_for_ldap_filter(group_dn)
    if recurse:
        ldap_filter = f'(&(memberOf:1.2.840.113556.1.4.1941:={group_dn})' \
                       '(objectCategory=person)(objectClass=user))'
    else:
        ldap_filter = f'(&(memberOf={group_dn})' \
                       '(objectCategory=person)(objectClass=user))'
    
    # ищем всех пользователей
    searched_users = get_ad_objects(ldap_filter, ['sAMAccountName'], path_dn, ad_conn)

    # проверяем наличие нашего пользователя в найденных, выводим результат
    for user in searched_users:
        if user.sAMAccountName.value == user_login:
            return True
    return False

def modify_ad_obj_attrs(obj_dn:str, modify_attrs:dict, ad_conn):
    """Изменение атрибутов объекта AD\n
    obj_dn - путь distinguishedName для объекта\n
    modify_attrs - атрибуты для изменения {attr1: value1, attr2: value2}\n
    ad_conn - соединитель Active Directory"""

    obj_dn = prepare_element_for_ldap_filter(obj_dn)
    ldap_filter = f'(distinguishedName={obj_dn})'

    # просто выводим ошибку если нет объекта с distinguishedName = obj_dn
    get_ad_objects(ldap_filter, [], obj_dn, ad_conn, error_if_empty=True)

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
            get_ad_objects(ldap_filter, [attr_key], obj_dn, ad_conn, error_if_empty=True)[0],
            attr_key    
        ).value
        if updated_attr_value != modify_attrs[attr_key]:
            raise PermissionError(f'Атрибут "{attr_key}" не изменён. Вероятно, недостаточно прав для этой операции.')
        
def clear_ad_obj_attrs(obj_dn:str, clear_attrs:[], ad_conn):
    """Очистка атрибутов объекта AD\n
    obj_dn - путь distinguishedName для объекта\n
    clear_attrs - массив имён атрибутов для очистки\n
    ad_conn - соединитель Active Directory"""

    obj_dn = prepare_element_for_ldap_filter(obj_dn)
    ldap_filter = f'(distinguishedName={obj_dn})'

    # просто выводим ошибку если нет объекта с distinguishedName = obj_dn
    get_ad_objects(ldap_filter, [], obj_dn, ad_conn, error_if_empty=True)

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
            get_ad_objects(ldap_filter, [attr_key], obj_dn, ad_conn, error_if_empty=True)[0],
            attr_key    
        ).value
        if updated_attr_value != None:
            raise PermissionError(f'Атрибут "{attr_key}" не очищен. Вероятно, недостаточно прав для этой операции.')

def prepare_element_for_ldap_filter(elem:str):
    """Подготовить элемент для LDAP-фильтра. Использовать всегда, если неизвестный элемент будет вставлен\n
    в фильтр. В группировке условий в LDAP-фильтре используются круглые скобки, если в нашем элементе\n
    будут скобки, фильтр их распознает, как группировочные и фильтрация закончится ошибкой. Необходимо\n
    скобки элемента заменить на спец.символы: '(' на '\\28', а ')' на '\\29'.\n
    elem - подготавливаемый для LDAP-фильтра элемент"""

    prepared_elem = elem \
                        .replace('(', '\\28') \
                        .replace(')', '\\29') \
                        .replace('*', '\\2a')

    return prepared_elem

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

    def get_ad_objects(self, ldap_filter:str, attributes:[], path_dn:str=None, error_if_empty=False):
        """Получить AD объекты по LDAP-фильтру\n
        ldapFilter - фильтр LDAP\n
        attributes - список искомых атрибутов\n
        path_dn - путь distinguishedName для поиска"""

        # __init__
        if path_dn is None:
            path_dn = self.search_dn

        search_objects = get_ad_objects(ldap_filter, attributes, path_dn, self.conn, error_if_empty)
        return search_objects

    def get_ad_objects_over_1000(self, ldap_filter:str, attributes:[], path_dn:str=None, error_if_empty=False):
        """Получить объекты по LDAP-фильтру без ограничений по их количеству
        ldap_filter - фильтр LDAP\n
        attributes - список искомых атрибутов\n
        path_dn - путь distinguishedName для поиска\n
        error_if_empty - если True вызовет исключение при пустом результате"""

        # __init__
        if path_dn is None:
            path_dn = self.search_dn
        
        search_objects = get_ad_objects_over_1000(ldap_filter, attributes, path_dn, self.conn, error_if_empty)
        return search_objects

    def get_ad_user(self, user_login:str, attrs:[], path_dn:str=None, error_if_empty=False):
        """Получить пользователя с необходимыми атрибутами по логину\n
        user_login - логин\n
        attrs - массив искомых атрибутов пользователя\n
        path_dn - dn путь для поиска. По умолчанию self.search_dn"""
        
        # __init__
        if path_dn is None:
            path_dn = self.search_dn
        
        searched_user = get_ad_user(user_login, attrs, path_dn, self.conn, error_if_empty)
        return searched_user

    def get_ad_group(self, group_login:str, attrs:[], path_dn:str=None, error_if_empty=False):
        """Получить группу с необходимыми атрибутами по логину (sAMAccountName)\n
        group_login - логин группы (это атрибут sAMAccountName)\n
        attrs - массив искомых атрибутов группы\n
        path_dn - dn путь для поиска. По умолчанию self.search_dn"""

        # __init__
        if path_dn is None:
            path_dn = self.search_dn
        
        searched_group = get_ad_group(group_login, attrs, path_dn, self.conn, error_if_empty)
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

    def check_ad_user_in_group(self, user_login:str, group_login:str, path_dn:str=None, recurse=True):
        """Проверяем наличие пользователя AD в группе AD
        user_login - логин пользователя\n
        group_login - логин группы\n
        path_dn - dn путь для поиска сотрудника и группы\n"""
                
        # __init__
        if path_dn is None:
            path_dn = self.search_dn

        return check_ad_user_in_group(user_login, group_login, path_dn, self.conn, recurse)

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
    def prepare_element_for_ldap_filter(elem:str):
        """Подготовить элемент для LDAP-фильтра. Использовать всегда, если неизвестный элемент будет вставлен\n
        в фильтр. В группировке условий в LDAP-фильтре используются круглые скобки, если в нашем элементе\n
        будут скобки, фильтр их распознает, как группировочные и фильтрация закончится ошибкой. Необходимо\n
        скобки элемента заменить на спец.символы: '(' на '\\28', а ')' на '\\29'.\n
        elem - подготавливаемый для LDAP-фильтра элемент"""

        return prepare_element_for_ldap_filter(elem)

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
