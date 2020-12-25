#region импорты
from ActiveDirectory import ActiveDirectory
from ActiveDirectory import (
    get_active_directory_conn,
    get_ad_objects,
    get_ad_user,
    get_ad_group,
    add_ad_user_to_group,
    remove_ad_user_from_group,
    verify_ad_user_in_group,
    convert_uac_to_dict,
    get_uac_attr
)

from config_private import (
    ad_servers,
    ad_login,
    ad_password,
    path_dn
)
#endregion


#region проверка функций
print('Проверка отдельных функций')
conn_func = get_active_directory_conn(ad_servers, ad_login, ad_password)

print('get_ad_objects()')
print(get_ad_objects('(&(objectCategory=person)(objectClass=user)(sAMAccountName=test23))', ['cn'], path_dn, conn_func)[0].cn == 'test23')
print(get_ad_objects('(&(objectCategory=group)(sAMAccountName=Test_Group))', ['cn'], path_dn, conn_func)[0].cn == 'Test_Group')
print(get_ad_objects('(&(objectCategory=groupjhj)(cn=asasdasd))', ['mail'], path_dn, conn_func) == [])

print('get_ad_user()')
print(get_ad_user('ывыаолдып', ['mail'], path_dn, conn_func) == None)
print(get_ad_user('test23', ['cn'], path_dn, conn_func).cn == 'test23')

print('get_ad_group()')
print(get_ad_group('fghsdfsdfs', ['whenCreated'], path_dn, conn_func) == None)
print(get_ad_group('Test_Group', ['cn'], path_dn, conn_func).cn == 'Test_Group')

print('add_ad_user_to_group(), remove_ad_user_from_group(), verify_ad_user_in_group()')
add_ad_user_to_group('test22', 'Test_Group', path_dn, conn_func)
print(True) if verify_ad_user_in_group('test22', 'Test_Group', path_dn, conn_func) else print(False)
remove_ad_user_from_group('test22', 'Test_Group', path_dn, conn_func)
print(False) if verify_ad_user_in_group('test22', 'Test_Group', path_dn, conn_func) else print(True)

print('convert_uac_to_dict()')
uac_dict = convert_uac_to_dict(66048)
print(uac_dict[8] == False)
print(uac_dict[512] == True)
print(uac_dict[65536] == True)

print('get_uac_attr()')
print(get_uac_attr(66048, 32) == False)
print(get_uac_attr(66048, 512) == True)
print(get_uac_attr(66048, 65536)== True)
# endregion


#region проверка Класса
print('\nПроверка методов Класса')
ad = ActiveDirectory(ad_servers, ad_login, ad_password, path_dn)

print('ad.get_ad_objects()')
print(ad.get_ad_objects('(&(objectCategory=person)(objectClass=user)(sAMAccountName=test23))', ['cn'])[0].cn == 'test23')
print(ad.get_ad_objects('(&(objectCategory=group)(sAMAccountName=Test_Group))', ['cn'])[0].cn == 'Test_Group')
print(ad.get_ad_objects('(&(objectCategory=groupjhj)(cn=asasdasd))', ['mail']) == [])

print('ad.get_ad_user()')
print(ad.get_ad_user('ывыаолдып', ['mail']) == None)
print(ad.get_ad_user('test23', ['cn']).cn == 'test23')

print('ad.get_ad_group()')
print(ad.get_ad_group('fghsdfsdfs', ['whenCreated']) == None)
print(ad.get_ad_group('Test_Group', ['cn']).cn == 'Test_Group')

print('ad.add_ad_user_to_group(), ad.remove_ad_user_from_group(), ad.verify_ad_user_in_group()')
ad.add_ad_user_to_group('test22', 'Test_Group')
print(True) if ad.verify_ad_user_in_group('test22', 'Test_Group') else print(False)
ad.remove_ad_user_from_group('test22', 'Test_Group')
print(False) if ad.verify_ad_user_in_group('test22', 'Test_Group') else print(True)

print('ad.convert_uac_to_dict()')
uac_dict = ad.convert_uac_to_dict(66048)
print(uac_dict[8] == False)
print(uac_dict[512] == True)
print(uac_dict[65536] == True)

print('ad.get_uac_attr()')
print(ad.get_uac_attr(66048, 32) == False)
print(ad.get_uac_attr(66048, 512) == True)
print(ad.get_uac_attr(66048, 65536)== True)
#endregion
