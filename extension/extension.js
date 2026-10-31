import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const COLORS=[[40,[51,157,255]],[30,[23,200,220]],[20,[50,200,137]],[10,[255,181,40]],[0,[255,66,83]]];
function color(margin) {
 for(let i=0;i<COLORS.length-1;i++) {
  const [hi,a]=COLORS[i], [lo,b]=COLORS[i+1];
  if(margin>=hi)return a;
  if(margin>=lo){const t=(hi-margin)/(hi-lo);return a.map((v,j)=>v+(b[j]-v)*t);}
 }
 return COLORS.at(-1)[1];
}
function size(n){return n>=1073741824?`${(n/1073741824).toFixed(1)} GB`:`${Math.round(n/1048576)} MB`;}
export default class HardwareBar extends Extension {
 enable(){
  this._alive=true;this._pending=new Set();this._fraction=0;this._target=0;this._rgb=[120,125,135];this._targetRgb=this._rgb;this._warning=false;this._last=0;
  this._button=new PanelMenu.Button(0.5,'Hardware temperature and memory');
  this._button.add_style_class_name('hardware-button');
  this._canvas=new St.DrawingArea({x_expand:true,y_expand:true});this._button.add_child(this._canvas);
  this._canvas.connect('repaint',()=>this._paint());
  Main.panel.add_child(this._button.container);Main.panel.menuManager.addMenu(this._button.menu);
  this._button.menu.box.add_style_class_name('hardware-menu');
  this._button.menu.actor.add_style_class_name('hardware-popover');
  this._body=new St.BoxLayout({orientation:Clutter.Orientation.VERTICAL,style_class:'hw-body'});
  this._button.menu.box.add_child(this._body);
  const label=(text,cls)=>new St.Label({text,style_class:cls});
  this._body.add_child(label('Hardware status','hw-title'));
  this._body.add_child(label('Live temperatures and memory','hw-subtitle'));
  const thermal=new St.BoxLayout({style_class:'hw-thermal'});this._body.add_child(thermal);
  this._tiles={};
  for(const name of ['CPU','SSD']){
   const tile=new St.BoxLayout({style_class:'hw-tile'});
   tile.add_child(new St.Icon({gicon:name==='CPU'?Gio.FileIcon.new(Gio.File.new_for_path(`${this.path}/thermometer-symbolic.svg`)):Gio.ThemedIcon.new('drive-harddisk-symbolic'),icon_size:30,style_class:'hw-sensor-icon'}));
   const stack=new St.BoxLayout({orientation:Clutter.Orientation.VERTICAL});
   stack.add_child(label(name,'hw-subtitle'));const value=label('—','hw-temperature');stack.add_child(value);tile.add_child(stack);thermal.add_child(tile);this._tiles[name]=value;
  }
  const statusBox=new St.BoxLayout({style_class:'hw-status',x_expand:true});
  this._statusIcon=new St.Icon({icon_name:'emblem-ok-symbolic',icon_size:24});statusBox.add_child(this._statusIcon);
  const statusText=new St.BoxLayout({orientation:Clutter.Orientation.VERTICAL,x_expand:true});
  this._thermal=label('Reading sensors…','hw-status-title');statusText.add_child(this._thermal);
  this._limits=label('Hardware-reported temperature limits','hw-subtitle');statusText.add_child(this._limits);statusBox.add_child(statusText);thermal.add_child(statusBox);
  const mem=new St.BoxLayout({style_class:'hw-memory'});mem.add_child(new St.Icon({icon_name:'media-flash-symbolic',icon_size:25}));
  const memStack=new St.BoxLayout({orientation:Clutter.Orientation.VERTICAL,x_expand:true,style_class:'hw-memory-stack'});
  this._memory=label('Memory','hw-memory-title');memStack.add_child(this._memory);
  const meterRow=new St.BoxLayout({style_class:'hw-meter-row'});
  this._menuCanvas=new St.DrawingArea({x_expand:true,height:12,y_align:Clutter.ActorAlign.CENTER});this._menuCanvas.connect('repaint',()=>this._paint(this._menuCanvas));meterRow.add_child(this._menuCanvas);
  this._percent=label('—','hw-subtitle');meterRow.add_child(this._percent);memStack.add_child(meterRow);mem.add_child(memStack);this._body.add_child(mem);
  const appHeading=new St.BoxLayout({style_class:'hw-app-heading'});appHeading.add_child(label('Applications','hw-app-title'));
  appHeading.add_child(new St.Widget({x_expand:true}));appHeading.add_child(label('Highest memory first','hw-subtitle'));
  const refresh=new St.Button({child:new St.Icon({icon_name:'view-refresh-symbolic',icon_size:15}),can_focus:true,style_class:'hw-refresh',accessible_name:'Refresh application list'});refresh.connect('clicked',()=>this._loadApps());appHeading.add_child(refresh);this._body.add_child(appHeading);
  const headers=new St.BoxLayout({style_class:'hw-headers'});const appLabel=label('Application','hw-subtitle');appLabel.x_expand=true;headers.add_child(appLabel);headers.add_child(label('Memory','hw-memory-column hw-subtitle'));headers.add_child(new St.Widget({style_class:'hw-action-column'}));this._body.add_child(headers);
  this._section=new PopupMenu.PopupMenuSection();
  const scroll=new St.ScrollView({style:'max-height: 350px;',overlay_scrollbars:true});scroll.set_child(this._section.actor);this._body.add_child(scroll);
  const footer=new St.BoxLayout({style_class:'hw-footer'});footer.add_child(label('App totals may differ from total RAM.','hw-subtitle'));footer.add_child(new St.Widget({x_expand:true}));footer.add_child(label('Kill stops immediately. Unsaved work is lost.','hw-subtitle'));this._body.add_child(footer);
  this._button.menu.connect('open-state-changed',(_m,open)=>{if(open){this._loadApps();this._menuCanvas.queue_repaint();}});
  this._timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,1500,()=>{this._sample();this._position();return GLib.SOURCE_CONTINUE;});
  this._frame=GLib.timeout_add(GLib.PRIORITY_DEFAULT,33,()=>{this._animate();return GLib.SOURCE_CONTINUE;});
  this._allocation=Main.panel.connect('notify::allocation',()=>this._position());
  this._position();this._sample();
 }
 _label(text,style){const item=new PopupMenu.PopupBaseMenuItem({reactive:false,can_focus:false});const label=new St.Label({text,style_class:style});item.add_child(label);this._button.menu.addMenuItem(item);return label;}
 _position(){
  if(!this._alive)return;
  const [px]=Main.panel.get_transformed_position();
  const left=Main.panel._leftBox;const [lx]=left.get_transformed_position();
  const clock=Main.panel.statusArea.dateMenu.container;const [cx]=clock.get_transformed_position();
  const [rx]=Main.panel._rightBox.get_transformed_position();
  const x=Math.round(lx-px+left.width+8);const end=Math.min(cx>lx+left.width?cx:rx,rx);
  const width=Math.max(0,Math.floor(end-px-x-8));
  const box=new Clutter.ActorBox({x1:x,y1:0,x2:x+width,y2:Main.panel.height});this._button.container.allocate(box);
 }
 async _run(mode,data){
  const args=['/usr/bin/python3',`${this.path}/metrics.py`,mode];if(data!==undefined)args.push(JSON.stringify(data));
  const proc=Gio.Subprocess.new(args,Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE);this._pending.add(proc);
  return await new Promise((resolve,reject)=>proc.communicate_utf8_async(null,null,(p,res)=>{
   this._pending.delete(proc);
   try{const [,out,err]=p.communicate_utf8_finish(res);if(!p.get_successful())throw new Error(err||'Hardware reader failed');resolve(JSON.parse(out));}catch(e){reject(e);}
  }));
 }
 async _sample(){
  if(this._busy)return;this._busy=true;
  try{
   const d=await this._run('metrics');if(!this._alive)return;
   this._target=Math.max(0,Math.min(1,d.used/d.total));
   this._targetRgb=d.worst?color(d.worst.margin):[130,135,145];this._warning=!!d.worst&&d.worst.margin<=10;
   const status=!d.worst?'Temperature unavailable':d.worst.margin<=0?'Hardware limit reached':d.worst.margin<=10?'Heat warning':d.worst.margin<=20?'Getting warm':'Normal';
   const rgb=this._targetRgb.map(Math.round).join(',');
   this._thermal.text=status;this._thermal.style=`color: rgb(${rgb});`;
   this._statusIcon.icon_name=this._warning?'dialog-warning-symbolic':'emblem-ok-symbolic';this._statusIcon.style=`color: rgb(${rgb});`;
   for(const [name,tile] of Object.entries(this._tiles)){const sensor=d.sensors.find(x=>x.label===name);tile.text=sensor?`${Math.round(sensor.temp)}°C`:'Unavailable';tile.style=sensor?`color: rgb(${color(sensor.margin).map(Math.round).join(',')});`:'';}
   this._memory.text=`Memory   ${size(d.used)} / ${size(d.total)}`;this._percent.text=`${Math.round(this._target*100)}%`;
   this._limits.text=d.sensors.map(s=>`${s.label} limit ${Math.round(s.limit)}°C`).join(' · ');
   this._button.accessible_name=`${status}. ${this._memory.text}`;
  }catch(e){if(this._alive){this._thermal.text='Sensor reading unavailable';this._targetRgb=[130,135,145];console.error(e);}}
  finally{this._busy=false;}
 }
 _animate(){
  const df=this._target-this._fraction;let changed=Math.abs(df)>0.0001;
  this._fraction+=df*0.13;
  this._rgb=this._rgb.map((v,i)=>{const d=this._targetRgb[i]-v;if(Math.abs(d)>0.1)changed=true;return v+d*0.13;});
  if(changed||this._lastWarning!==this._warning){this._canvas.queue_repaint();if(this._button.menu.isOpen)this._menuCanvas.queue_repaint();this._lastWarning=this._warning;}
 }
 _paint(area=this._canvas){
  const cr=area.get_context();const [w,h]=area.get_surface_size();const thick=Math.min(9,h-4);const y=(h-thick)/2;
  function pill(x,y,width,height){const r=Math.min(height/2,width/2);cr.newSubPath();cr.arc(x+width-r,y+r,r,-Math.PI/2,0);cr.arc(x+width-r,y+height-r,r,0,Math.PI/2);cr.arc(x+r,y+height-r,r,Math.PI/2,Math.PI);cr.arc(x+r,y+r,r,Math.PI,Math.PI*1.5);cr.closePath();}
  if(w>2&&thick>0){pill(1,y,w-2,thick);cr.setSourceRGBA(.19,.21,.24,1);cr.fill();const fw=Math.max(2,(w-2)*this._fraction);pill(1,y,fw,thick);cr.setSourceRGBA(...this._rgb.map(v=>v/255),1);cr.fill();if(this._warning){pill(1,y,w-2,thick);cr.setSourceRGBA(1,.25,.3,1);cr.setLineWidth(1.5);cr.stroke();}}
  cr.$dispose();
 }
 async _loadApps(){
  if(this._appsBusy)return;this._appsBusy=true;
  try{
   const apps=Shell.AppSystem.get_default().get_running().filter(a=>a.get_windows().length);
   const spec=apps.map(a=>({id:a.get_id(),pids:[...new Set(a.get_windows().map(w=>w.get_pid()).filter(p=>p>1))]}));
   const rows=await this._run('apps',spec);if(!this._alive)return;this._section.removeAll();
   if(!rows.length){this._section.addMenuItem(new PopupMenu.PopupMenuItem('No open applications',{reactive:false}));}
   for(const row of rows){
    const app=apps.find(a=>a.get_id()===row.id);if(!app||!row.count)continue;
    const item=new PopupMenu.PopupBaseMenuItem({reactive:false,can_focus:false});item.add_style_class_name('hardware-row');
    item.add_child(app.create_icon_texture(28));
    const labels=new St.BoxLayout({orientation:Clutter.Orientation.VERTICAL,x_expand:true});labels.add_child(new St.Label({text:app.get_name()}));labels.add_child(new St.Label({text:`${row.count} ${row.count===1?'process':'processes'}`,style_class:'hw-subtitle'}));item.add_child(labels);
    item.add_child(new St.Label({text:size(row.rss),y_align:Clutter.ActorAlign.CENTER,style_class:'hw-memory-column'}));
    const kill=new St.Button({label:'Kill',style_class:'hardware-kill',can_focus:true,accessible_name:`Kill ${app.get_name()}`});item.add_child(kill);
    kill.connect('clicked',async()=>{kill.reactive=false;kill.label='Stopping…';try{const result=await this._run('kill',row.tokens);if(this._alive){kill.label=result.killed?'Stopped':'Already closed';}}catch(e){if(this._alive){kill.label='Failed';kill.reactive=true;}console.error(e);}});
    this._section.addMenuItem(item);
   }
  }catch(e){console.error(e);}finally{this._appsBusy=false;}
 }
 disable(){
  this._alive=false;for(const id of [this._timer,this._frame])if(id)GLib.source_remove(id);
  if(this._allocation)Main.panel.disconnect(this._allocation);
  for(const p of this._pending)p.force_exit();this._pending.clear();this._button.destroy();this._button=null;
 }
}
