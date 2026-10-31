#!/usr/bin/python3
"""Read only hardware and process accounting, never file contents or command lines."""
import os,json,sys,signal
from pathlib import Path

def number(p):
 try:return float(p.read_text().strip())
 except (OSError,ValueError):return None

def metrics():
 mem={k:int(v.split()[0])*1024 for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines())}
 sensors=[]
 for h in Path('/sys/class/hwmon').glob('hwmon*'):
  try:name=(h/'name').read_text().strip()
  except OSError:continue
  if name not in ('coretemp','nvme','xe','i915','amdgpu'):continue
  for p in h.glob('temp*_input'):
   stem=p.name[:-6];t=number(p);crit=number(h/(stem+'_crit'));high=number(h/(stem+'_max'))
   if t is None or not -20000<t<150000:continue
   if crit is not None and not 20000<crit<150000:crit=None
   if high is not None and not 20000<high<150000:high=None
   if crit is None and high is None:continue
   limit=min(x for x in (crit,high) if x is not None)/1000
   label='CPU' if name=='coretemp' else 'SSD' if name=='nvme' else 'GPU'
   # Early caution margins are policy, hardware limit itself is driver reported.
   sensors.append(dict(label=label,temp=t/1000,limit=limit,margin=limit-t/1000))
 groups=[]
 for label in ('CPU','GPU','SSD'):
  candidates=[x for x in sensors if x['label']==label]
  if candidates:groups.append(min(candidates,key=lambda x:x['margin']))
 worst=min(groups,key=lambda x:x['margin']) if groups else None
 return dict(total=mem['MemTotal'],used=mem['MemTotal']-mem['MemAvailable'],sensors=groups,worst=worst)

def processes():
 result={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   if p.stat().st_uid!=os.getuid():continue
   raw=(p/'stat').read_text();end=raw.rfind(')');f=raw[end+2:].split()
   result[int(p.name)]=dict(pid=int(p.name),ppid=int(f[1]),start=f[19],rss=max(0,int(f[21]))*os.sysconf('SC_PAGE_SIZE'),name=raw[raw.find('(')+1:end])
  except (OSError,ValueError,IndexError):continue
 return result

def descendants(roots,ps):
 found=set(roots)&ps.keys()
 while True:
  added={pid for pid,p in ps.items() if p['ppid'] in found}-found
  if not added:return found
  found|=added

def apps(spec):
 ps=processes();out=[];claimed=set()
 for app in spec:
  roots=[int(x) for x in app['pids'] if int(x)>1]
  ids=descendants(roots,ps)-claimed;claimed|=ids
  # RSS is explicit: shared memory may be counted more than once.
  out.append(dict(id=app['id'],rss=sum(ps[p]['rss'] for p in ids),count=len(ids),tokens=[[p,ps[p]['start']] for p in ids]))
 return sorted(out,key=lambda x:x['rss'],reverse=True)

def kill(tokens):
 ps=processes();killed=0
 protected={'gnome-shell','systemd','dbus-daemon','dbus-broker','Xwayland','pipewire','wireplumber'}
 for pid,start in tokens:
  p=ps.get(int(pid))
  if not p or p['start']!=str(start) or p['name'] in protected or int(pid) in (os.getpid(),os.getppid(),1):continue
  try:
   fd=os.pidfd_open(int(pid))
   # Verify identity again after obtaining a race-safe process handle.
   now=processes().get(int(pid))
   if now and now['start']==str(start):signal.pidfd_send_signal(fd,signal.SIGKILL);killed+=1
   os.close(fd)
  except (OSError,ProcessLookupError):pass
 return {'killed':killed}
if __name__=='__main__':
 mode=sys.argv[1]
 print(json.dumps(metrics() if mode=='metrics' else apps(json.loads(sys.argv[2])) if mode=='apps' else kill(json.loads(sys.argv[2])) if mode=='kill' else {}))
