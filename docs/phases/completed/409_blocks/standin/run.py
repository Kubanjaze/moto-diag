import os, subprocess, shutil, tempfile, sys, pty, pathlib
HERE=os.path.dirname(os.path.abspath(__file__))
B=os.path.dirname(HERE)+'/'
BIN=HERE+'/bin'
REPO=os.path.abspath(HERE+'/../../../../..')
PY=os.environ.get('STANDIN_PY', REPO+'/.venv')
PRIV_OLD='<p>Cloudflare, which serves it, keeps standard request logs.</p>'
PRIV_NEW=open(REPO+'/site/privacy/index.html').read()
def world(newcode=True, ts_ok=True, cf=False, privacy_new=True, env_extra=''):
    h=pathlib.Path(tempfile.mkdtemp())
    st=h/'st'; st.mkdir(); binw=h/'bin'; shutil.copytree(BIN,binw)
    (h/'.config/motodiag').mkdir(parents=True)
    env=f"MOTODIAG_ENV=prod\nMOTODIAG_TERMS_REQUIRED=true\nMOTODIAG_STRIPE_API_KEY=sk_test_planted\n{env_extra}"
    (h/'.config/motodiag/server.env').write_text(env); (st/'running.env').write_text(env)
    srv=h/'motodiag/server'; (srv/'src/motodiag/auth').mkdir(parents=True)
    os.symlink(PY, srv/'.venv')
    if newcode: (srv/'src/motodiag/auth/login_throttle.py').write_text('#'); (st/'newcode').write_text('')
    if ts_ok: (st/'ts_ok').write_text('')
    if cf: (st/'cf_active').write_text(''); shutil.copy(HERE+'/pkg/cloudflared', binw/'cloudflared')
    (st/'privacy.html').write_text(PRIV_NEW if privacy_new else PRIV_OLD)
    (st/'ss8000').write_text('LISTEN 0 2048 127.0.0.1:8000 0.0.0.0:*\n')
    (st/'ssall').write_text('LISTEN 0 2048 127.0.0.1:8000 0.0.0.0:*\nLISTEN 0 128 100.75.113.50:22 0.0.0.0:*\n')
    return h
def run(block, h, tty_input=None):
    e={'HOME':str(h),'ST':str(h/'st'),'STBIN':str(h/'bin'),'STPKG':HERE+'/pkg','PATH':f"{h/'bin'}:/usr/bin:/bin"}
    if tty_input is None:
        r=subprocess.run(['bash',B+block],env=e,capture_output=True,text=True,stdin=subprocess.DEVNULL, start_new_session=True)
        return r.stdout+r.stderr
    pid,fd=pty.fork()
    if pid==0:
        os.execve('/bin/bash',['bash',B+block],e)
    out=b''; sent=False
    while True:
        try: d=os.read(fd,4096)
        except OSError: break
        if not d: break
        out+=d
        if not sent and b'press Enter' in out:
            # Type only once read -s has turned echo off, as a person pasting
            # after the prompt would; typing at once raced it under load and
            # the pty echoed the token (the advisor, 3 of 8 runs on a busy Mac).
            # After 10 s it types anyway, so a block that never turns echo
            # off still shows the token and fails its case.
            import termios, time
            t=time.monotonic()+10
            while termios.tcgetattr(fd)[3] & termios.ECHO and time.monotonic()<t: time.sleep(0.01)
            os.write(fd,(tty_input+'\n').encode()); sent=True
    os.waitpid(pid,0); return out.decode(errors='replace')
def env_of(h): return (h/'.config/motodiag/server.env').read_text()
def last(o): return [l for l in o.strip().splitlines() if l.strip()][-1]
R=[]
def case(name, ok, detail=''):
    R.append((name, ok)); print(('PASS ' if ok else 'FAIL ')+name+(' :: '+detail if not ok else ''))
