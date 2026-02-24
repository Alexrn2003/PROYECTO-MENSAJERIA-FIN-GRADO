import os
from ldap3 import Server, Connection, ALL, NTLM
from dotenv import load_dotenv

load_dotenv()
LDAP_SERVER = os.getenv('LDAP_SERVER')
LDAP_PORT = int(os.getenv('LDAP_PORT','389'))
BASE_DN = os.getenv('BASE_DN')
LDAP_ADMIN_USER = os.getenv('LDAP_ADMIN_USER')
LDAP_ADMIN_PASSWORD = os.getenv('LDAP_ADMIN_PASSWORD')
DOMAIN = os.getenv('DOMAIN')

if not LDAP_SERVER or not LDAP_ADMIN_PASSWORD:
    print('Falta configuración LDAP en .env (LDAP_SERVER o LDAP_ADMIN_PASSWORD)')
    raise SystemExit(1)

print('Conectando a LDAP:', LDAP_SERVER)
server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL)
admin_dn = f"{LDAP_ADMIN_USER}@{DOMAIN}"
try:
    conn = Connection(server, user=admin_dn, password=LDAP_ADMIN_PASSWORD, auto_bind=True)
except Exception as e:
    print('Error al bindear como admin:', e)
    raise SystemExit(1)

search_filter = '(objectClass=user)'
attributes = ['sAMAccountName','userPrincipalName','displayName','mail','userAccountControl','pwdLastSet','lockoutTime']
print('Buscando usuarios en', BASE_DN)
conn.search(BASE_DN, search_filter, attributes=attributes, paged_size=250)

print('\nResultados:')
for entry in conn.entries:
    sam = str(entry.sAMAccountName) if 'sAMAccountName' in entry and entry.sAMAccountName else ''
    upn = str(entry.userPrincipalName) if 'userPrincipalName' in entry and entry.userPrincipalName else ''
    disp = str(entry.displayName) if 'displayName' in entry and entry.displayName else ''
    mail = str(entry.mail) if 'mail' in entry and entry.mail else ''
    uac = int(entry.userAccountControl.value) if 'userAccountControl' in entry and entry.userAccountControl else 0
    pwdLastSet = str(entry.pwdLastSet) if 'pwdLastSet' in entry and entry.pwdLastSet else ''
    lockout = str(entry.lockoutTime) if 'lockoutTime' in entry and entry.lockoutTime else ''

    disabled = bool(uac & 0x2)
    must_change_pwd = (pwdLastSet == '0')

    print(f"- {sam} | UPN: {upn} | Name: {disp} | mail: {mail}")
    print(f"    userAccountControl: {uac} (disabled={disabled}) pwdLastSet={pwdLastSet} must_change_pwd={must_change_pwd} lockoutTime={lockout}")

conn.unbind()
print('\nFin de auditoría')
