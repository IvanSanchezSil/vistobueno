// Prueba local del contrato de eventos extraído. No ejecuta la aplicación Angular.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root=process.env.VISTOBUENO_AUDIT_ROOT || path.resolve(__dirname,'../..');
const {JSDOM}=require(require.resolve('jsdom',{paths:[path.join(root,'tools/dspace-fill')]}));
const {aplicarPlan}=require(path.join(root,'tools/dspace-fill/src/ejecutor.js'));
const methods=JSON.parse(fs.readFileSync(path.join(__dirname,'contrato_widget.json'),'utf8')).methods;
const template=methods.find(e=>e.moduleId===83766 && e.method==='optionTemplate');
const select=methods.find(e=>e.moduleId===83766 && e.method==='onSelect');
const dispatch=methods.find(e=>e.moduleId===54875 && e.method==='dispatchUpdate');
const source='<input id="dc_rights" readonly><div id="combobox_dc_rights_listbox"><button type="button" title="Acceso abierto">Acceso abierto</button></div>';
async function run() {
	// Recursos externos y ejecución de scripts de la página desactivados por defecto.
	const dom=new JSDOM(source);
	const doc=dom.window.document;
	const option=doc.querySelector('#combobox_dc_rights_listbox button[title="Acceso abierto"]');
	assert.ok(option);
	const entry={display:'Acceso abierto',value:'https://purl.org/coar/access_right/c_abf2'};
	let dirty=0,changes=0;
	const component={model:{value:'PREVIOUS_SELECTION'},group:{markAsDirty(){dirty++;}},change:{emit(){changes++;}},setCurrentValue(){}};
	component.onSelect=vm.runInNewContext('({'+select.code+'}).onSelect');
	component.dispatchUpdate=vm.runInNewContext('({'+dispatch.code+'}).dispatchUpdate');
	const registered=[];
	const angular={
		RV6(){return {};},j41(){},nI1(){},EFF(){},k0s(){},
		eBV(){return {$implicit:entry};},XpG(){return component;},sdS(){return {close(){}};},Njj(value){return value;},
		bIt(event,handler){
			registered.push(event);
			if(event==='keydown.enter') option.addEventListener('keydown',e=>{if(e.key==='Enter')handler();});
			else option.addEventListener(event,handler);
			return angular.bIt;
		}
	};
	vm.runInNewContext('('+template.code+')',{t:angular})(1,{$implicit:entry});
	assert.deepEqual(registered,['keydown.enter','mousedown']);
	const result=await aplicarPlan(doc,{operaciones:[{tipo:'combobox',selectorInput:'input#dc_rights',selectorListbox:'#combobox_dc_rights_listbox',texto:'Acceso abierto'}],omitidos:[]},{dormir:async()=>{}});
	assert.deepEqual(result.exitosos,['combobox']);
	assert.equal(component.model.value,'PREVIOUS_SELECTION');
	assert.equal(changes,0);
	const before={reportedSuccess:true,modelChanged:false,changeEmissions:changes,dirtyCalls:dirty};
	option.dispatchEvent(new dom.window.MouseEvent('mousedown',{bubbles:true}));
	assert.equal(component.model.value,entry);
	assert.equal(changes,1);
	assert.equal(dirty,1);
	const report={scope:'Plantilla y métodos extraídos con helpers simulados y DOM ficticio; no es una integración Angular completa',registeredEvents:registered,currentExecutor:before,controlMousedown:{modelChanged:true,changeEmissions:changes,dirtyCalls:dirty}};
	fs.writeFileSync(path.join(__dirname,'resultado_dropdown.json'),JSON.stringify(report,null,2));
	console.log(JSON.stringify(report,null,2));
	dom.window.close();
}
run().catch(e=>{console.error(e.message);process.exitCode=1;});
