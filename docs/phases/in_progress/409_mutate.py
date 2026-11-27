import sys,subprocess,shutil,os
P='src/motodiag/launch/check.py'
orig=open(P).read()
muts={
 "docs check dropped":('    if code != 404:\n','    if False:\n'),
 "shops check dropped":('    if code != 401:\n','    if False:\n'),
 "health check dropped":('    if not healthy:\n','    if False:\n'),
 "scheme check dropped":('    if urlsplit(raw).scheme != "https":\n','    if False:\n'),
 "host refusal dropped":('    if _host_is_unreachable_publicly(parts.hostname):\n','    if False:\n'),
 "reader path refusal dropped":(' or path not in {p for p, _ in PUBLIC_PROBES}',''),
 "proxy bypass dropped":('        urllib.request.ProxyHandler({}),\n',''),
 "cert error not named":('                return Condition(name, False, "the certificate is not valid")\n','                return Condition(name, False, "the public address did not answer")\n'),
 "not in run_conditions":('        public_condition(settings),\n',''),
}
res={}
for k,(a,b) in muts.items():
    assert orig.count(a)>=1,k
    open(P,'w').write(orig.replace(a,b,1))
    r=subprocess.run([sys.executable,'-m','pytest','-q','-x','-p','no:cacheprovider','tests/test_phase409_public_condition.py','tests/test_phase210_launch_check.py'],env=dict(os.environ,PYTHONPATH='src',PYTHONUTF8='1'),capture_output=True,text=True)
    res[k]='RED' if r.returncode!=0 else 'survived'
    print(k,res[k],flush=True)
open(P,'w').write(orig)
