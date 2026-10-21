const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map();
const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',showModal(){this.open=true;}});return nodes.get(id)},querySelectorAll(){return []}};
const context={document,console,assert};vm.createContext(context);
let script=fs.readFileSync('static/app.js','utf8');script=script.slice(0,script.indexOf("$('quarantine').onclick="));
vm.runInContext(script+`
const sample={id:'a',source:'s',kind:'map',format:'PGM map',name:'20260919-135337 / map',path:'/maps/20260919-135337/map.pgm',relative_path:'20260919-135337/map.pgm',display_group:'g',bytes:10,category:'glim',topics:[],images:[],warnings:[],date_basis:'folder',files:[],can_delete:true,can_trash:true};
const copy={...sample,id:'b',name:'20260919-135337（コピー） / map',path:'/maps/20260919-135337（コピー）/map.pgm'};
catalog.items=[copy,sample];
const cards=displayItems(catalog.items);assert.equal(cards.length,1);assert.equal(cards[0].id,'a');assert.equal(cards[0].copies.length,2);assert.equal(cards[0].bytes,10);assert.equal(cards[0].total_bytes,20);assert.equal(cards[0].can_trash,false);
assert.ok(card(cards[0]).includes('2 保存先'));
details('a');const html=$('detail-body').innerHTML;
assert.ok(html.includes(sample.path));assert.ok(html.includes(copy.path));assert.ok(html.includes('data-open-folder="a"'));assert.ok(html.includes('data-open-folder="b"'));
assert.equal((html.match(/delete-item/g)||[]).length,2);
assert.equal($('quarantine').hidden,true);
assert.equal(displayItems([{...sample,display_group:undefined},{...copy,display_group:undefined}]).length,2);
`,context);
console.log('Copy grouping, detail links and per-location deletion UI passed.');
