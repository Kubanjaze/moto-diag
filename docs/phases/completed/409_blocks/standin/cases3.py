__file__ = __import__('os').path.abspath(__file__)
exec(open(__import__('os').path.join(__import__('os').path.dirname(__file__), 'run.py')).read())
import subprocess as sp
h=world(); run('4_server_settings.txt',h); tok='T'*90+'secretTOKEN'+'T'*60; o=run('6_tunnel_installed.txt',h,tty_input=tok)
case('6 the token is not shown', last(o)=='ALL GOOD' and 'secretTOKEN' not in o, o)
# 3a / 3c against a local origin holding this branch as master
h=world(); bare=h/'origin.git'
sp.run(['git','init','-q','--bare',str(bare)],check=True)
sp.run(['git','-C',REPO,'push','-q',str(bare),'HEAD:refs/heads/master'],check=True)
(h/'Projects').mkdir(exist_ok=True)
sp.run(['git','clone','-q',str(bare),str(h/'Projects/moto-diag')],check=True)
(h/'Downloads').mkdir()
e={'HOME':str(h),'ST':str(h/'st'),'STBIN':str(h/'bin'),'PATH':f"{h/'bin'}:/usr/bin:/bin"}
o=run('3a_site_upload_file.txt',h)
case('3a builds the zip from master', last(o)=='ALL GOOD' and (h/'Downloads/getmekno-site-409.zip').exists(), o)
for p in ('terms','privacy'):
    (h/f'st/{p}.html').write_text(open(f'{REPO}/site/{p}/index.html').read())
o=run('3c_site_check.txt',h)
case('3c live pages are master\'s: ALL GOOD', last(o)=='ALL GOOD', o)
(h/'st/privacy.html').write_text(open(REPO+'/site/privacy/index.html').read().replace('Version 1.2','Version 1.1'))
o=run('3c_site_check.txt',h)
case('3c old privacy page live: OFF', 'is not master\'s page yet' in o, o)
(h/'st/privacy.html').unlink(); o=run('3c_site_check.txt',h)
case('3c page cannot be opened: OFF', 'could not open' in o or "not master's page" in o, o)
sp.run(['git','-C',REPO,'push','-q','-f',str(bare),'origin/master:refs/heads/master'],check=True)
o=run('3a_site_upload_file.txt',h)
case('3a before the merge (master at 1.1): OFF', 'does not say Version 1.2' in o, o)
print(f"{sum(ok for _,ok in R)}/{len(R)} cases pass")
