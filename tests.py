from . import ActiveDirectory
from . import (
    get_active_directory_conn,
    get_ad_objects,
    get_ad_objects_over_1000,
    get_ad_user,
    get_ad_group,
    add_ad_user_to_group,
    remove_ad_user_from_group,
    check_ad_user_in_group,
    modify_ad_obj_attrs,
    clear_ad_obj_attrs,
    convert_uac_to_dict,
    get_uac_attr
)
from .config_private import (
    ad_servers,
    ad_login,
    ad_password,
    path_dn
)
import random

conn_func = get_active_directory_conn(ad_servers, ad_login, ad_password)
ad = ActiveDirectory(ad_servers, ad_login, ad_password, path_dn)

#region проверка функций
print('Проверка отдельных функций')

    #region get_ad_objects()
print('          get_ad_objects()')
print(
    get_ad_objects('(&(objectCategory=person)(objectClass=user)(sAMAccountName=test23))', ['cn'], path_dn, conn_func)[0].cn == 'test23'
    and get_ad_objects('(&(objectCategory=group)(sAMAccountName=Test_Group))', ['cn'], path_dn, conn_func)[0].cn == 'Test_Group'
    and get_ad_objects('(&(objectCategory=groupjhj)(cn=asasdasd))', ['mail'], path_dn, conn_func) == []
)
try: get_ad_objects('(&(objectCategory=groupjhj)(cn=asasdasd))', ['mail'], path_dn, conn_func, error_if_empty=True)
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (&(objectCategory=groupjhj)(cn=asasdasd))')
    #endregion

    #region get_ad_objects_over_1000()
print('          get_ad_objects_over_1000()')
print(
    len(get_ad_objects_over_1000('(objectClass=user)', [], path_dn, conn_func)) > 1000
    and get_ad_objects_over_1000('(mail=test22@tesli.com)', ['sAMAccountName'], path_dn, conn_func)[0].sAMAccountName == 'test22'
    and len(get_ad_objects_over_1000('(mail=asfg)', [], path_dn, conn_func)) == 0
)
try: get_ad_objects_over_1000('(mail=asfg)', [], path_dn, conn_func, error_if_empty=True)
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (mail=asfg)')
    #endregion

    #region get_ad_user()
print('          get_ad_user()')
print(
    get_ad_user('test23', ['cn'], path_dn, conn_func).cn == 'test23'
    and get_ad_user('ывыаолдып', ['mail'], path_dn, conn_func) == None
)
try: get_ad_user('ывыаолдып', ['mail'], path_dn, conn_func, error_if_empty=True)
except ValueError as err: print(err.__str__() == 'Пользователь с логином "ывыаолдып" не найден')
    #endregion

    #region get_ad_group()
print('          get_ad_group()')
print(
    get_ad_group('Test_Group', ['cn'], path_dn, conn_func).cn == 'Test_Group'
    and get_ad_group('fghsdfsdfs', ['whenCreated'], path_dn, conn_func) == None
)
try: get_ad_group('fghsdfsdfs', ['whenCreated'], path_dn, conn_func, error_if_empty=True)
except ValueError as err: print(err.__str__() == 'Группа с логином "fghsdfsdfs" не найдена')
    #endregion

    #region add_ad_user_to_group(), remove_ad_user_from_group(), check_ad_user_in_group()
print('          add_ad_user_to_group(), remove_ad_user_from_group(), check_ad_user_in_group()')
add_ad_user_to_group('test22', 'Test_Group', path_dn, conn_func)
print(check_ad_user_in_group('test22', 'Test_Group', path_dn, conn_func))
remove_ad_user_from_group('test22', 'Test_Group', path_dn, conn_func)
print(not check_ad_user_in_group('test22', 'Test_Group', path_dn, conn_func))
try: add_ad_user_to_group('test212', 'Test_Group', path_dn, conn_func)
except ValueError as err: print(err.__str__() == 'Пользователь с логином "test212" не найден')
try: add_ad_user_to_group('test22', 'Test_Group11', path_dn, conn_func)
except ValueError as err: print(err.__str__() == 'Группа с логином "Test_Group11" не найдена')
try: remove_ad_user_from_group('test212', 'Test_Group', path_dn, conn_func)
except ValueError as err: print(err.__str__() == 'Пользователь с логином "test212" не найден')
try: remove_ad_user_from_group('test22', 'Test_Group11', path_dn, conn_func)
except ValueError as err: print(err.__str__() == 'Группа с логином "Test_Group11" не найдена')
try: check_ad_user_in_group('test22', 'Test_Group1111', path_dn, conn_func)
except ValueError as err: print(err.__str__() == 'Группа с логином "Test_Group1111" не найдена')
    #endregion

    #region modify_ad_obj_attrs()
print('          modify_ad_obj_attrs()')
obj_dn = get_ad_user('test22', ['distinguishedName'], path_dn, conn_func).distinguishedName.value
rand_str = str(random.getrandbits(44))
modify_ad_obj_attrs(obj_dn, {'sn': rand_str, 'displayName': rand_str}, conn_func)
print(
    get_ad_user('test22', ['sn'], path_dn, conn_func).sn.value == rand_str
    and get_ad_user('test22',['displayName'], path_dn, conn_func).displayName.value == rand_str
)
try: modify_ad_obj_attrs('CN=test2333,DC=ts,DC=main', {'displayName': rand_str}, conn_func)
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (distinguishedName=CN=test2333,DC=ts,DC=main)')
    #endregion

    #region clear_ad_obj_attrs()
print('          clear_ad_obj_attrs()')
obj_dn = get_ad_user('test23', ['distinguishedName'], path_dn, conn_func).distinguishedName.value
clear_ad_obj_attrs(obj_dn, ['sn', 'displayName'], conn_func)
print(
    get_ad_user('test23', ['sn'], path_dn, conn_func).sn.value == None
    and get_ad_user('test23',['displayName'], path_dn, conn_func).displayName.value == None
)
try: clear_ad_obj_attrs('CN=test2333,DC=ts,DC=main', ['company'], conn_func)
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (distinguishedName=CN=test2333,DC=ts,DC=main)')
    #endregion

    #region convert_uac_to_dict()
print('          convert_uac_to_dict()')
uac_dict = convert_uac_to_dict(66048)
print(
    uac_dict[8] == False
    and uac_dict[512] == True
    and uac_dict[65536] == True
)
    #endregion

    #region get_uac_attr()
print('          get_uac_attr()')
print(
    get_uac_attr(66048, 32) == False
    and get_uac_attr(66048, 512) == True
    and get_uac_attr(66048, 65536)== True
)
    #endregion
# endregion


#region проверка Класса
print('\nПроверка методов Класса')

    #region ad.get_ad_objects()
print('          ad.get_ad_objects()')
print(
    ad.get_ad_objects('(&(objectCategory=person)(objectClass=user)(sAMAccountName=test23))', ['cn'])[0].cn == 'test23'
    and ad.get_ad_objects('(&(objectCategory=group)(sAMAccountName=Test_Group))', ['cn'])[0].cn == 'Test_Group'
    and ad.get_ad_objects('(&(objectCategory=groupjhj)(cn=asasdasd))', ['mail']) == []
)
try: ad.get_ad_objects('(&(objectCategory=groupjhj)(cn=asasdasd))', ['mail'], error_if_empty=True)
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (&(objectCategory=groupjhj)(cn=asasdasd))')
    #endregion

    #region get_ad_objects_over_1000()
print('          get_ad_objects_over_1000()')
print(
    len(ad.get_ad_objects_over_1000('(objectClass=user)', [])) > 1000
    and ad.get_ad_objects_over_1000('(mail=test22@tesli.com)', ['sAMAccountName'])[0].sAMAccountName == 'test22'
    and len(ad.get_ad_objects_over_1000('(mail=asfg)', [])) == 0
)
try: ad.get_ad_objects_over_1000('(mail=asfg)', [], error_if_empty=True)
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (mail=asfg)')
    #endregion

    #region ad.get_ad_user()
print('          ad.get_ad_user()')
print(
    ad.get_ad_user('test23', ['cn']).cn == 'test23'
    and ad.get_ad_user('ывыаолдып', ['mail']) == None
)
try: ad.get_ad_user('ывыаолдып', ['mail'], error_if_empty=True)
except ValueError as err: print(err.__str__() == 'Пользователь с логином "ывыаолдып" не найден')
    #endregion

    #region ad.get_ad_group()
print('          ad.get_ad_group()')
print(
    ad.get_ad_group('Test_Group', ['cn']).cn == 'Test_Group'
    and ad.get_ad_group('fghsdfsdfs', ['whenCreated']) == None
)
try: ad.get_ad_group('fghsdfsdfs', ['whenCreated'], error_if_empty=True)
except ValueError as err: print(err.__str__() == 'Группа с логином "fghsdfsdfs" не найдена')
    #endregion

    #region ad.add_ad_user_to_group(), ad.remove_ad_user_from_group(), ad.check_ad_user_in_group()
print('          ad.add_ad_user_to_group(), ad.remove_ad_user_from_group(), ad.check_ad_user_in_group()')
ad.add_ad_user_to_group('test22', 'Test_Group')
print(ad.check_ad_user_in_group('test22', 'Test_Group'))
ad.remove_ad_user_from_group('test22', 'Test_Group')
print(not ad.check_ad_user_in_group('test22', 'Test_Group'))
try: ad.add_ad_user_to_group('test212', 'Test_Group')
except ValueError as err: print(err.__str__() == 'Пользователь с логином "test212" не найден')
try: ad.add_ad_user_to_group('test22', 'Test_Group11')
except ValueError as err: print(err.__str__() == 'Группа с логином "Test_Group11" не найдена')
try: ad.remove_ad_user_from_group('test212', 'Test_Group')
except ValueError as err: print(err.__str__() == 'Пользователь с логином "test212" не найден')
try: ad.remove_ad_user_from_group('test22', 'Test_Group11')
except ValueError as err: print(err.__str__() == 'Группа с логином "Test_Group11" не найдена')
try: ad.check_ad_user_in_group('test223456', 'Test_Group')
except ValueError as err: print(err.__str__() == 'Пользователь с логином "test223456" не найден')
try: ad.check_ad_user_in_group('test22', 'Test_Group1111')
except ValueError as err: print(err.__str__() == 'Группа с логином "Test_Group1111" не найдена')
    #endregion

    #region ad.modify_ad_obj_attrs()
print('          ad.modify_ad_obj_attrs()')
obj_dn = ad.get_ad_user('test23', ['distinguishedName'], path_dn).distinguishedName.value
rand_str = str(random.getrandbits(44))
ad.modify_ad_obj_attrs(obj_dn, {'sn': rand_str, 'displayName': rand_str})
print(
    ad.get_ad_user('test23', ['sn'], path_dn).sn.value == rand_str
    and ad.get_ad_user('test23',['displayName'], path_dn).displayName.value == rand_str
)
try: ad.modify_ad_obj_attrs('CN=test2333,DC=ts,DC=main', {'displayName': rand_str})
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (distinguishedName=CN=test2333,DC=ts,DC=main)')
    #endregion

    #region ad.clear_ad_obj_attrs()
print('          ad.clear_ad_obj_attrs()')
obj_dn = ad.get_ad_user('test23', ['distinguishedName'], path_dn).distinguishedName.value
ad.clear_ad_obj_attrs(obj_dn, ['sn', 'displayName'])
print(
    ad.get_ad_user('test23', ['sn'], path_dn).sn.value == None
    and ad.get_ad_user('test23',['displayName'], path_dn).displayName.value == None
)
try: ad.clear_ad_obj_attrs('CN=test2333,DC=ts,DC=main', ['company'])
except ValueError as err: print(err.__str__() == 'По заданному LDAP-фильтру не найден ни один объект. LDAP-фильтр: (distinguishedName=CN=test2333,DC=ts,DC=main)')
    #endregion

    #region ad.convert_uac_to_dict()
print('          ad.convert_uac_to_dict()')
uac_dict = ad.convert_uac_to_dict(66048)
print(
    uac_dict[8] == False
    and uac_dict[512] == True
    and uac_dict[65536] == True
)
    #endregion

    #region ad.get_uac_attr()
print('          ad.get_uac_attr()')
print(
    ad.get_uac_attr(66048, 32) == False
    and ad.get_uac_attr(66048, 512) == True
    and ad.get_uac_attr(66048, 65536)== True
)
    #endregion
#endregion
