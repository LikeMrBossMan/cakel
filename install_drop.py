#!/usr/bin/env python3
"""
Safely install the Drop workflow and Door 5 parking selector into
/home/app/blank/templates/index.html.

This script is intentionally conservative:
- it checks expected V25 markers before changing anything;
- creates and verifies a timestamped backup;
- writes the template only after all transformations pass validation;
- never opens or modifies the vehicle database.
"""

from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

TEMPLATE = Path("/home/app/blank/templates/index.html")
BACKUP_DIR = Path("/home/app/v25-backup/drop-workflow")


def fail(message):
    print("STOP:", message, file=sys.stderr)
    raise SystemExit(1)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected exactly one match, found {count}. No changes written.")
    return text.replace(old, new, 1)


def find_function_bounds(text, name):
    match = re.search(r"\bfunction\s+" + re.escape(name) + r"\s*\(", text)
    if not match:
        fail(f"Could not find function {name}(). No changes written.")
    brace = text.find("{", match.start())
    depth = 0
    quote = None
    escaped = False
    i = brace

    while i < len(text):
        ch = text[i]
        pair = text[i:i + 2]

        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif pair == "//":
            newline = text.find("\n", i)
            i = len(text) if newline < 0 else newline
            continue
        elif pair == "/*":
            close = text.find("*/", i + 2)
            if close < 0:
                fail(f"Unclosed JavaScript comment while reading {name}().")
            i = close + 2
            continue
        elif ch in ("'", '"', "`"):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return match.start(), i + 1
        i += 1

    fail(f"Could not safely find the end of {name}().")


def replace_function(text, name, replacement):
    start, end = find_function_bounds(text, name)
    return text[:start] + replacement + text[end:]


def find_assignment_end(text, start, opening_brace):
    """Find the matching brace for the save arrow-function body."""
    depth = 0
    quote = None
    escaped = False
    i = opening_brace

    while i < len(text):
        ch = text[i]
        pair = text[i:i + 2]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif pair == "//":
            newline = text.find("\n", i)
            i = len(text) if newline < 0 else newline
            continue
        elif pair == "/*":
            close = text.find("*/", i + 2)
            if close < 0:
                fail("Unclosed comment in save handler.")
            i = close + 2
            continue
        elif ch in ("'", '"', "`"):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                # Include a trailing semicolon if present.
                return i + 2 if text[i + 1:i + 2] == ";" else i + 1
        i += 1
    fail("Could not safely find the end of the save handler.")


def replace_save_handler(text, replacement):
    marker = "$('save').onclick=async()=>{"
    if text.count(marker) != 1:
        fail("Expected one save handler marker; no changes written.")
    start = text.find(marker)
    brace = text.find("{", start)
    end = find_assignment_end(text, start, brace)
    return text[:start] + replacement + text[end:]


def main():
    if not TEMPLATE.is_file():
        fail(f"Template not found: {TEMPLATE}")

    original = TEMPLATE.read_text(encoding="utf-8")
    if 'id="dropTab"' in original or 'id="dropOptions"' in original:
        fail("Drop UI already exists. Refusing to apply a duplicate patch.")

    required = [
        ('<nav class="nav"><button id="dirtyTab" class="on">🚿 Dirty</button><button id="cleanTab" class="clean">✨ Clean</button></nav>', "navigation"),
        ("function selectMode(v){", "selectMode"),
        ("function setStep(n){", "setStep"),
        ("function reset(keepMode){", "reset"),
        ("function buildQuickNumOptions(){", "buildQuickNumOptions"),
        ("function rowRender(){", "rowRender"),
        ("function review(){", "review"),
        ("function render(){", "render"),
        ("$('save').onclick=async()=>{", "save handler"),
        ("$('dirtyTab').onclick=()=>selectMode('dirty');$('cleanTab').onclick=()=>selectMode('clean');", "tab handlers"),
        ('<button type="button" class="rowpick" data-rowpick="D">D</button>', "D picker"),
        ('<div class="actions"><button id="back2">', "page 2 insertion point"),
        ("</head>", "head close"),
        ("mode='dirty',step=1,selectedRow='A',selectedNum=1,destination='Washbay'", "state variables"),
    ]
    for marker, label in required:
        if original.count(marker) != 1:
            fail(f"Preflight failed for {label}: expected one match, found {original.count(marker)}.")

    text = original

    # Add the Drop tab and workflow controls.
    text = replace_once(
        text,
        '<nav class="nav"><button id="dirtyTab" class="on">🚿 Dirty</button><button id="cleanTab" class="clean">✨ Clean</button></nav>',
        '<nav class="nav"><button id="dirtyTab" class="on">🚿 Dirty</button><button id="cleanTab" class="clean">✨ Clean</button><button id="dropTab">📦 Drop</button></nav>',
        "navigation",
    )

    drop_html = """
<div id="dropOptions" class="hide">
<h2>📦 Drop workflow</h2>
<p class="muted">Did you?</p>
<div class="drop-actions">
<label><input type="radio" name="dropAction" value="picked_up" checked> Picked Up</label>
<label><input type="radio" name="dropAction" value="dropped_off"> Dropped Off</label>
</div>
<label for="dropLocation">Where?</label>
<select id="dropLocation" style="width:100%;padding:12px;border-radius:10px;background:#071528;color:white;border:1px solid #7392b8">
<option>AV West</option><option>AV</option><option>Castle</option><option>First Energy</option><option>Smuckers</option>
</select>
<div id="dropReadyWrap" class="hide">
<label for="dropReadySpot">Ready parking spot</label>
<input id="dropReadySpot" value="A12" maxlength="3" placeholder="A12">
</div>
<p class="muted" id="dropRouteHint">AV West → Washbay</p>
</div>
"""
    text = replace_once(
        text,
        '<div class="actions"><button id="back2">',
        drop_html + '<div class="actions"><button id="back2">',
        "Drop controls insertion",
    )

    text = replace_once(
        text,
        "mode='dirty',step=1,selectedRow='A',selectedNum=1,destination='Washbay'",
        "mode='dirty',step=1,selectedRow='A',selectedNum=1,destination='Washbay',dropAction='picked_up',dropLocation='AV West',dropReadySpot='A12'",
        "state variables",
    )

    text = replace_function(text, "selectMode", """function selectMode(v){
mode=v;
$('dirtyTab').classList.toggle('on',v==='dirty');
$('cleanTab').classList.toggle('on',v==='clean');
$('dropTab').classList.toggle('on',v==='drop');
$('folderHeading').textContent=(v==='dirty'?'Dirty':v==='clean'?'Clean':'Drop')+' vehicles';
$('search').value='';
setStep(1);
render();
}""")

    tab_marker = "$('dirtyTab').onclick=()=>selectMode('dirty');$('cleanTab').onclick=()=>selectMode('clean');"
    text = replace_once(text, tab_marker, tab_marker + """
$('dropTab').onclick=()=>selectMode('drop');
function syncDropControls(){
const radio=document.querySelector('input[name="dropAction"]:checked');
dropAction=radio?radio.value:'picked_up';
dropLocation=$('dropLocation').value;
dropReadySpot=$('dropReadySpot').value.trim().toUpperCase();
$('dropReadyWrap').classList.toggle('hide',dropAction!=='dropped_off');
$('dropRouteHint').textContent=dropAction==='picked_up'
?dropLocation+' → Washbay':dropReadySpot+' → '+dropLocation;
}
document.querySelectorAll('input[name="dropAction"]').forEach(x=>x.onchange=syncDropControls);
$('dropLocation').onchange=syncDropControls;
$('dropReadySpot').oninput=syncDropControls;
syncDropControls();
""", "tab handlers")

    text = replace_function(text, "setStep", """function setStep(n){
step=n;
for(let i=1;i<=3;i++)$('page'+i).classList.toggle('hide',i!==n);
$('stepLabel').textContent='STEP '+n+' OF 3';
document.querySelectorAll('.dots i').forEach((e,i)=>e.classList.toggle('on',i<n));
$('cleanOptions').classList.toggle('hide',mode!=='clean');
$('dirtyOptions').classList.toggle('hide',mode!=='dirty');
$('dropOptions').classList.toggle('hide',mode!=='drop');
if(n===3)review();
$('wizard').scrollIntoView({behavior:'smooth',block:'start'});
}""")

    text = replace_once(
        text,
        '<button type="button" class="rowpick" data-rowpick="D">D</button>',
        '<button type="button" class="rowpick" data-rowpick="D">D</button><button type="button" class="rowpick" data-rowpick="Door 5">Door 5</button>',
        "Door 5 picker",
    )

    text = replace_function(text, "buildQuickNumOptions", """function buildQuickNumOptions(){
const sel=$('quickNum');if(!sel)return;
sel.replaceChildren();
if(selectedRow==='Door 5'){
const o=document.createElement('option');o.value='1';o.textContent='Door 5';sel.append(o);
sel.value='1';sel.disabled=true;return;
}
sel.disabled=false;
const max=selectedRow==='D'?16:25;
for(let n=max;n>=1;n--){const o=document.createElement('option');o.value=String(n);o.textContent=selectedRow+n;sel.append(o)}
if(selectedNum>max)selectedNum=max;
sel.value=String(selectedNum);
}""")

    text = replace_function(text, "rowRender", """function rowRender(){
const grid=$('lotGrid');if(!grid)return;
grid.replaceChildren();
for(let n=25;n>=1;n--){
for(const col of ['A','B','gap','C','D']){
if(col==='gap'){
const gap=document.createElement(n===1?'button':'div');
gap.className='lot-gap';
if(n===1){
gap.type='button';gap.classList.add('door-five');gap.textContent='Door 5';
gap.setAttribute('aria-label','Select Door 5');
gap.onclick=()=>{
selectedRow='Door 5';selectedNum=1;
document.querySelectorAll('.rowpick').forEach(x=>x.classList.toggle('on',x.dataset.rowpick==='Door 5'));
buildQuickNumOptions();rowRender();
};
}
grid.append(gap);continue;
}
const btn=document.createElement('button');btn.type='button';btn.className='lot-cell';
if(col==='D'&&n>16){btn.classList.add('empty');btn.disabled=true;grid.append(btn);continue;}
const spot=col+n;btn.textContent=spot;btn.dataset.spot=spot;
btn.setAttribute('aria-label','Parking spot '+spot);
const chosen=selectedRow===col&&selectedNum===n;
const occupied=records.some(r=>isCurrentDay(r)&&isClean(r)&&r.spot===spot);
if(chosen)btn.classList.add('chosen');else if(occupied)btn.classList.add('occupied');
btn.onclick=()=>{
selectedRow=col;selectedNum=n;
document.querySelectorAll('.rowpick').forEach(x=>x.classList.toggle('on',x.dataset.rowpick===col));
buildQuickNumOptions();$('quickNum').value=String(n);rowRender();
};
grid.append(btn);
}}
const spot=selectedRow==='Door 5'?'Door 5':selectedRow+selectedNum;
$('tagColor').textContent=selectedRow==='Door 5'?'🚪 Door 5':
(selectedRow==='A'||selectedRow==='B'?'🟡 Yellow tag • A/B rows':'🔴 Red tag • C/D rows');
const occupied=records.some(r=>isCurrentDay(r)&&isClean(r)&&r.spot===spot);
$('spotPreview').textContent='Selected spot: '+spot+(occupied?' · Already occupied':'');
}""")

    # Adapt picker handlers without changing unrelated event wiring.
    picker_handler = "document.querySelectorAll('.rowpick').forEach(b=>b.onclick=()=>{selectedRow=b.dataset.rowpick;selectedNum=Math.min(selectedNum,selectedRow==='D'?16:25);document.querySelectorAll('.rowpick').forEach(x=>x.classList.toggle('on',x===b));buildQuickNumOptions();rowRender()});"
    if text.count(picker_handler) != 1:
        fail("Quick-picker handler didn't match the expected V25 version.")
    text = text.replace(picker_handler, """document.querySelectorAll('.rowpick').forEach(b=>b.onclick=()=>{
selectedRow=b.dataset.rowpick;
if(selectedRow==='Door 5')selectedNum=1;
else selectedNum=Math.min(selectedNum,selectedRow==='D'?16:25);
document.querySelectorAll('.rowpick').forEach(x=>x.classList.toggle('on',x===b));
buildQuickNumOptions();rowRender();
});""", 1)

    text = replace_once(
        text,
        "$('quickNum').onchange=()=>{selectedNum=Number($('quickNum').value);rowRender()};",
        "$('quickNum').onchange=()=>{if(selectedRow!=='Door 5'){selectedNum=Number($('quickNum').value);rowRender()}};",
        "quick number handler",
    )
    text = replace_once(
        text,
        "$('jumpSpot').onclick=()=>{selectedNum=Number($('quickNum').value);rowRender();$('spotPreview').scrollIntoView({behavior:'smooth',block:'center'})};",
        "$('jumpSpot').onclick=()=>{if(selectedRow!=='Door 5')selectedNum=Number($('quickNum').value);rowRender();$('spotPreview').scrollIntoView({behavior:'smooth',block:'center'})};",
        "jump handler",
    )

    text = replace_function(text, "reset", """function reset(keepMode){
if(imageUrl)URL.revokeObjectURL(imageUrl);
imageUrl='';imageFile=null;imageTime=0;vinMeta={};
$('photoInput').value='';$('closeup').value='';$('vin').value='';
$('vinMode').value='last';$('vinMode').onchange();
$('preview').classList.add('hide');$('finalPhoto').classList.add('hide');
setMsg('scanMsg','');setMsg('saveMsg','');
destination='Washbay';dropAction='picked_up';dropLocation='AV West';dropReadySpot='A12';
document.querySelector('input[name="dropAction"][value="picked_up"]').checked=true;
$('dropLocation').value='AV West';$('dropReadySpot').value='A12';syncDropControls();
selectedRow='A';selectedNum=1;
document.querySelectorAll('[data-dest]').forEach(b=>b.classList.toggle('sel',b.dataset.dest==='Washbay'));
document.querySelectorAll('.rowpick').forEach(x=>x.classList.toggle('on',x.dataset.rowpick==='A'));
if($('quickNum')){buildQuickNumOptions();$('quickNum').value='1';}
setStep(1);rowRender();
}""")

    text = replace_function(text, "review", r"""function review(){
const spot=selectedRow==='Door 5'?'Door 5':selectedRow+selectedNum;
const vin=norm($('vin').value);
$('finalPhoto').src=imageUrl;$('finalPhoto').classList.remove('hide');
const summary=mode==='clean'?'Clean · Washbay → '+spot:
mode==='dirty'?'Dirty · Return Line → '+destination:
dropAction==='picked_up'?'Drop · Picked Up · '+dropLocation+' → Washbay':
'Drop · Dropped Off · '+dropReadySpot+' → '+dropLocation;
$('finalInfo').textContent=summary+'\nLast 8 VIN: '+(vin||'Not entered')+'\nTime: '+time(imageTime);
$('finalInfo').style.whiteSpace='pre-line';
}""")

    # Change only the existing gallery filter, preserving its rendering logic.
    old_filter = "records.filter(r=>isCurrentDay(r)&&isClean(r)===(mode==='clean'))"
    new_filter = "records.filter(r=>isCurrentDay(r)&&(mode==='drop'?(r.workflow==='drop'||r.folder==='Drop'):r.workflow!=='drop'&&r.folder!=='Drop'&&isClean(r)===(mode==='clean')))"
    text = replace_once(text, old_filter, new_filter, "gallery filter")

    # Save workflow records in the existing record structure.
    save_code = r"""$('save').onclick=async()=>{
if(!imageFile||!db)return;
syncDropControls();
const drop=mode==='drop',vin=norm($('vin').value),ts=imageTime||Date.now();
if(drop&&dropAction==='dropped_off'){
if(!/^[ABCD](?:[1-9]|1[0-9]|2[0-5])$/.test(dropReadySpot)||
(dropReadySpot[0]==='D'&&Number(dropReadySpot.slice(1))>16)){
setMsg('saveMsg','Enter a valid Ready spot such as A12 (D spaces end at D16).',true);return;
}}
const matches=vin?records.filter(r=>isCurrentDay(r)&&norm(r.vin)===vin):[];
const same=drop?matches.find(r=>r.workflow==='drop'||r.folder==='Drop'):
mode==='clean'?matches.find(r=>isClean(r)):
matches.find(r=>!isClean(r)&&r.workflow!=='drop'&&r.folder!=='Drop');
const previous=mode==='clean'?matches.find(r=>!isClean(r)&&r.workflow!=='drop'&&r.folder!=='Drop'):null;
if(same&&!confirm('This VIN is already saved in '+mode+'. Update its record?'))return;
const spot=mode==='clean'?(selectedRow==='Door 5'?'Door 5':selectedRow+selectedNum):
drop&&dropAction==='dropped_off'?dropReadySpot:'';
if(mode==='clean'){
const occupied=records.find(r=>isCurrentDay(r)&&isClean(r)&&r.spot===spot&&norm(r.vin)!==vin);
if(occupied&&!confirm('Parking spot '+spot+' is occupied. Save anyway?'))return;
}
const button=$('save');button.disabled=true;
try{
const meta=vinMeta.vin===vin?vinMeta:{};
let pickup,dropoff,route,folder;
if(mode==='clean'){
pickup='Washbay';dropoff=spot;route='Washbay → '+spot;folder='Clean Parking';
}else if(mode==='dirty'){
pickup='Return Line';dropoff=destination;route='Return Line → '+destination;folder='Down to Washbay';
}else if(dropAction==='picked_up'){
pickup=dropLocation;dropoff='Washbay';route=dropLocation+' → Washbay';folder='Drop';
}else{
pickup=dropReadySpot;dropoff=dropLocation;route=dropReadySpot+' → '+dropLocation;folder='Drop';
}
const entry={
fullVin:fullVin()||same?.fullVin||previous?.fullVin||'',
id:same?.id||previous?.id||crypto.randomUUID(),
folder,workflow:drop?'drop':mode,dropAction:drop?dropAction:'',
dropLocation:drop?dropLocation:'',
blob:imageFile,name:imageFile.name,timestamp:ts,addedAt:Date.now(),vin,
year:meta.year||same?.year||previous?.year||'',
make:meta.make||same?.make||previous?.make||'',
model:meta.model||same?.model||previous?.model||'',
spot,route,pickup,dropoff,
dirtyTime:mode==='clean'?(previous?.dirtyTime||previous?.timestamp||same?.dirtyTime||null):
mode==='dirty'?ts:(same?.dirtyTime||null),
cleanTime:mode==='clean'?ts:(same?.cleanTime||null)
};
await transact('put',entry);
if(previous&&same&&previous.id!==same.id)await transact('delete',previous.id);
await refresh();
setMsg('saveMsg','✓ Saved '+(vin||'photo')+' to '+mode+'.');
reset();setMsg('scanMsg','✓ Saved to server! Ready for the next vehicle.');
}catch(e){setMsg('saveMsg','Could not save: '+e.message,true)}
finally{button.disabled=false}
};"""
    text = replace_save_handler(text, save_code)

    css = """
<style>
#dropTab.on{background:#214675;color:#fff}
#dropOptions{padding:12px 0}
#dropOptions label{display:block;margin:10px 0}
#dropOptions input[type=radio]{width:auto}
.lot-grid-head,.lot-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr) 64px minmax(0,1fr) minmax(0,1fr)!important}
.lot-gap.door-five{display:flex;align-items:center;justify-content:center;text-align:center;min-width:0;padding:3px;color:#fff;font-weight:800;font-size:11px;background:#214675;border:1px solid #7392b8;border-radius:6px;cursor:pointer}
.rowpick[data-rowpick="Door 5"]{font-size:12px;padding-left:4px;padding-right:4px}
@media(max-width:520px){.lot-grid-head,.lot-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr) 52px minmax(0,1fr) minmax(0,1fr)!important}}
</style>
"""
    text = replace_once(text, "</head>", css + "\n</head>", "CSS insertion")

    # Final checks before backup/write.
    for label, marker in [
        ("Drop tab", 'id="dropTab"'),
        ("Drop controls", 'id="dropOptions"'),
        ("Picked Up / Dropped Off", 'name="dropAction"'),
        ("AV West", "AV West"),
        ("AV", "<option>AV</option>"),
        ("Castle", "Castle"),
        ("First Energy", "First Energy"),
        ("Smuckers", "Smuckers"),
        ("Door 5 picker", 'data-rowpick="Door 5"'),
        ("Door 5 grid marker", "gap.classList.add('door-five')"),
        ("Drop gallery filter", "mode==='drop'?(r.workflow==='drop'"),
        ("Photo VIN scanner retained", "async function scan()"),
        ("Admin history guard retained", "typeof renderAdminHistory==='function'"),
    ]:
        if marker not in text:
            fail(f"Final validation failed: {label}. No changes written.")

    # Verify that only intended template text is changed; create backup first.
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / (
        "index-before-drop-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".html"
    )
    shutil.copy2(TEMPLATE, backup)
    if backup.read_bytes() != TEMPLATE.read_bytes():
        fail("Backup verification failed. Live template not written.")

    TEMPLATE.write_text(text, encoding="utf-8")
    if TEMPLATE.read_text(encoding="utf-8") != text:
        shutil.copy2(backup, TEMPLATE)
        fail("Post-write verification failed; original template restored from backup.")

    print("PATCH INSTALLED")
    print("Backup:", backup)
    print("Template:", TEMPLATE)
    print("Original size:", len(original), "characters")
    print("Updated size:", len(text), "characters")
    print("Saved vehicle database was not opened or modified.")


if __name__ == "__main__":
    main()
