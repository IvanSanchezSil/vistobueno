/* Auditoría offline: reproduce defectos de la base c9e5499. No corrige código.
 * Ejecutar: node docs/auditoria_userscript_2026-11-16/reproducir.cjs
 * Requiere npm ci en tools/dspace-fill. Se puede usar VISTOBUENO_AUDIT_ROOT.
 * Los casos afirman el comportamiento defectuoso observado. Al corregirlo,
 * trasladar el caso a la suite del área e invertir la condición de aceptación.
 */
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=process.env.VISTOBUENO_AUDIT_ROOT || path.resolve(__dirname,'../..');
const {JSDOM}=require(require.resolve('jsdom',{paths:[path.join(root,'tools/dspace-fill')]}));
const executor=require(path.join(root,'tools/dspace-fill/src/ejecutor.js'));
const mapper=require(path.join(root,'tools/dspace-fill/src/mapeador.js'));
const gates=require(path.join(root,'tools/dspace-fill/src/compuertas.js'));
const parts=['compuertas','mapeador','ejecutor','reloj','wrapper'];
const source=parts.map(name=>fs.readFileSync(path.join(root,'tools/dspace-fill/src',name+'.js'),'utf8')).join('\n');
const S=gates.SELECTORES;
const form=()=>`<form><input name="dc.title"><input name="dc.contributor.author"><input name="dc.contributor.advisor"><textarea name="dc.description.abstract"></textarea><input name="dc.subject"><input id="dc_date_issued_year"><input id="dc_rights"><div id="combobox_dc_rights_listbox"><button type="button">Acceso abierto</button></div><button type="button" id="deposit">Depositar</button></form>`;
const item=(title='Tesis ficticia A',handle='https://hdl.handle.net/20.500.14414/900001')=>`<html><head><meta name="citation_title" content="${title}"></head><body><h1>${title}</h1><a href="${handle}">${handle}</a></body></html>`;
function envelope(id='t-a',title='Tesis ficticia A') {return {tramite_id:id,vence_en:'2099-01-01T00:00:00Z',ficha:{extraidos:[{campo:'dc.title',valor:title},{campo:'dc.contributor.author',valor:['Autora ficticia A']},{campo:'dc.contributor.advisor',valor:'Asesor ficticio A'},{campo:'dc.description.abstract',valor:'Resumen ficticio A'},{campo:'dc.subject',valor:['Educación']},{campo:'dc.date.issued',valor:'2026'}],manuales:[]}};}
function dom(text) {return new JSDOM(text);}
const fast={dormir:async()=>{}};
const result=[];
async function check(id,fn) {const details=await fn();result.push({id,status:'reproducido',details});}
function mount({html=form(),env=null,reply=envelope(),networkError=false,defer=false,hook=null,store=new Map()}={}) {
	const d=new JSDOM(html,{url:'https://repositorio.unitru.edu.pe/workspaceitems/900001/edit',runScripts:'outside-only'});
	const w=d.window;const calls=[];const held=[];const tasks=new Map();let serial=0,now=Date.UTC(2026,10,16,15);
	const NativeDate=w.Date;
	w.Date=class extends NativeDate {constructor(...args){super(...(args.length?args:[now]));}static now(){return now;}};
	w.setTimeout=(fn,delay=0,...args)=>{const id=++serial;tasks.set(id,{at:now+Number(delay),fn:()=>fn(...args)});return id;};
	w.clearTimeout=id=>tasks.delete(id);
	w.GM_getValue=(key,fallback)=>store.has(key)?structuredClone(store.get(key)):fallback;
	w.GM_setValue=(key,value)=>store.set(key,structuredClone(value));
	if(env)store.set('vb_envio',structuredClone(env));
	let currentReply=reply;
	w.GM_xmlhttpRequest=options=>{
		const call={method:options.method,url:options.url,body:options.data?JSON.parse(options.data):null,options};calls.push(call);
		if(options.method==='GET') {
			const respond=()=>{if(networkError)options.onerror?.({error:'simulated'});else options.onload({status:200,responseText:JSON.stringify(currentReply)});};
			if(defer)held.push(respond);else respond();
		}else options.onload?.({status:204,responseText:''});
	};
	if(hook)w.__auditHook=hook;
	const executable=hook?source.replace('// Wrapper del rellenador:','window.__auditHook(VBEjecutor);\n// Wrapper del rellenador:'):source;
	try { w.eval(executable); } catch(error) { d.window.close(); throw error; }
	async function flush(){for(let i=0;i<5;i++)await Promise.resolve();await new Promise(resolve=>setImmediate(resolve));}
	async function advance(ms=1000){
		const target=now+ms;await flush();let count=0;
		while(true){let pick=null;for(const [id,t]of tasks)if(t.at<=target&&(!pick||t.at<pick[1].at))pick=[id,t];if(!pick)break;
			if(++count>2000)throw new Error('Bucle de temporizadores en el caso');now=pick[1].at;tasks.delete(pick[0]);pick[1].fn();await flush();
		}now=target;await flush();
	}
	return {d,w,doc:w.document,calls,held,store,advance,setReply(value){currentReply=value;},close(){d.window.close();tasks.clear();}};
}
(async()=>{
	await check('EX-01',async()=>{
		const d=dom('<input name="x" disabled>');const r=await executor.aplicarPlan(d.window.document,{operaciones:[{tipo:'texto',selector:'input',valor:'nuevo'}],omitidos:[]},fast);assert.deepEqual(r.exitosos,['texto']);d.window.close();return 'Control disabled: informa éxito.';
	});
	await check('EX-02',async()=>{
		const d=dom('<input name="x" value="anterior">');const el=d.window.document.querySelector('input');el.addEventListener('input',()=>el.value='anterior');const r=await executor.aplicarPlan(d.window.document,{operaciones:[{tipo:'texto',selector:'input',valor:'nuevo'}],omitidos:[]},fast);assert.equal(el.value,'anterior');assert.deepEqual(r.exitosos,['texto']);d.window.close();return 'Listener restaura valor; el ejecutor informa éxito.';
	});
	await check('EX-03',async()=>{
		const d=dom('<input name="x" hidden><input name="x">');const r=await executor.aplicarPlan(d.window.document,{operaciones:[{tipo:'texto',selector:'input[name="x"]',valor:'nuevo'}],omitidos:[]},fast);assert.equal(d.window.document.querySelectorAll('input')[1].value,'');assert.deepEqual(r.exitosos,['texto']);d.window.close();return 'Selector duplicado: rellena el oculto y deja el visible vacío.';
	});
	await check('EX-04',async()=>{
		const d=dom('<select name="meta"><option value="0: renati.author.dni">DNI</option></select><input name="id">');const doc=d.window.document;doc.querySelector('select').addEventListener('change',()=>doc.querySelector('input').replaceWith(doc.createElement('input')));const r=await executor.aplicarPlan(doc,{operaciones:[{tipo:'qualdrop',selectorMeta:'select',selectorValor:'input',opcionSufijo:'renati.author.dni',valores:['11111111']}],omitidos:[]},fast);assert.equal(doc.querySelector('input').value,'');assert.deepEqual(r.exitosos,['qualdrop']);d.window.close();return 'Reemplazo de input tras change: escribe en el nodo desconectado y declara éxito. Simula render; no afirma que ocurra siempre en UNT.';
	});
	await check('EX-05',async()=>{
		const d=dom('<input name="author" value="A"><input name="author" value="persona anterior">');const doc=d.window.document;const r=await executor.aplicarPlan(doc,{operaciones:[{tipo:'filas',selector:'input',valores:['persona nueva']}],omitidos:[]},fast);assert.equal(doc.querySelectorAll('input').length,2);assert.equal(doc.querySelectorAll('input')[1].value,'persona anterior');assert.deepEqual(r.exitosos,['filas']);d.window.close();return '2→1 filas: conserva datos sobrantes y declara éxito.';
	});
	await check('EX-06',async()=>{
		const ficha=envelope().ficha;ficha.extraidos.find(x=>x.campo==='dc.contributor.author').valor=['Autora A','Autor B'];ficha.manuales=[{campo:'renati.author.dni',valor:['','22222222']}];const plan=mapper.construirPlan(ficha,S);assert.deepEqual(plan.operaciones.find(x=>x.tipo==='qualdrop').valores,['22222222']);return 'El DNI de la posición 2 pasa a posición 1; no hay validación del par autor/DNI.';
	});
	await check('EX-07',async()=>{
		const d=dom('<select><option value="1: renati.author.pasaporte">Pasaporte</option></select><input value="PASAPORTE-ANTERIOR">');const r=await executor.aplicarPlan(d.window.document,{operaciones:[{tipo:'qualdrop',selectorMeta:'select',selectorValor:'input',opcionSufijo:'renati.author.dni',valores:['11111111']}],omitidos:[]},fast);assert.deepEqual(r.fallidos,['qualdrop']);assert.equal(d.window.document.querySelector('input').value,'11111111');d.window.close();return 'Falta opción DNI: falla, pero sobrescribe el número conservando tipo Pasaporte.';
	});
	await check('EX-08',async()=>{
		const d=dom('<input id="rights" value="Acceso restringido"><div id="options"></div>');const r=await executor.aplicarPlan(d.window.document,{operaciones:[{tipo:'combobox',selectorInput:'#rights',selectorListbox:'#options',texto:'Acceso abierto'}],omitidos:[]},fast);assert.deepEqual(r.fallidos,['combobox']);assert.equal(d.window.document.querySelector('input').value,'');d.window.close();return 'Fallo del combobox borra el texto previo en vez de restaurarlo. La política abierta está aprobada; el problema es recuperación del fallo.';
	});
	await check('EX-09',async()=>{
		const d=dom('<input id="present">');const r=await executor.aplicarPlan(d.window.document,{operaciones:[{tipo:'texto',selector:'#missing',valor:'x'},{tipo:'texto',selector:'#present',valor:'y'}],omitidos:[]},fast);assert.deepEqual(r.exitosos,['texto']);assert.deepEqual(r.fallidos,['texto']);assert.equal(r.exitosos[0],r.fallidos[0]);d.window.close();return 'El resumen solo identifica tipos: no distingue qué campo texto falló y cuál pasó.';
	});
	await check('WR-01',async()=>{
		const m=mount({html:form().replace('<input name="dc.contributor.advisor">','')});await m.advance();assert.equal(m.store.get('vb_envio').tramite_id,'t-a');const input=m.doc.createElement('input');input.name='dc.contributor.advisor';m.doc.querySelector('form').append(input);m.doc.querySelector('#vb-boton').click();await m.advance();assert.equal(input.value,'');assert.match(m.doc.querySelector('#vb-toast').textContent,/no se volvió/);m.close();return 'Fallo parcial se guarda como lleno; el botón no permite completar el campo aparecido tarde.';
	});
	await check('WR-02',async()=>{
		const m=mount({networkError:true});await m.advance(2000);assert.equal(m.doc.querySelector('#vb-boton'),null);assert.equal(m.calls.length,1);m.close();return 'Fallo inicial de red deja el formulario sin botón de rescate ni nueva consulta.';
	});
	await check('WR-03',async()=>{
		const m=mount({html:form().replace('<input name="dc.title">','<input name="dc.title" value="TRÁMITE AJENO">')});await m.advance();assert.equal(m.doc.querySelector(S.titulo).value,'Tesis ficticia A');m.close();return 'Auto-relleno sobrescribe un formulario con título ajeno sin diagnóstico ni confirmación.';
	});
	await check('WR-04',async()=>{
		const pending=[];const m=mount({hook:E=>{E.aplicarPlan=()=>new Promise(resolve=>pending.push(resolve));}});assert.equal(pending.length,1);m.setReply(envelope('t-b','Tesis ficticia B'));m.doc.querySelector('#vb-boton').click();assert.equal(pending.length,2);pending[1]({exitosos:[],fallidos:[],omitidos:[]});await m.advance(1);assert.equal(m.store.get('vb_envio').tramite_id,'t-b');pending[0]({exitosos:[],fallidos:[],omitidos:[]});await m.advance(1);assert.equal(m.store.get('vb_envio').tramite_id,'t-a');m.close();return 'Dos rellenos simultáneos: callback viejo termina después y reemplaza el trámite nuevo.';
	});
	await check('WR-05',async()=>{
		const m=mount({defer:true});assert.equal(m.held.length,1);m.w.history.pushState({},'','/workspaceitems/900002/edit');m.doc.querySelector(S.titulo).value='OTRO BORRADOR';m.held[0]();await m.advance();assert.equal(m.doc.querySelector(S.titulo).value,'Tesis ficticia A');m.close();return 'Respuesta pendiente del buzón rellena otro workspace tras navegar.';
	});
	await check('WR-06',async()=>{
		const m=mount({env:{tramite_id:'t-a',titulo:'Tesis ficticia A',timestamp:null},reply:{}});await m.advance();m.doc.querySelector(S.titulo).value='Otra tesis en otro borrador';m.doc.querySelector('#deposit').click();assert.ok(m.store.get('vb_envio').timestamp);assert.equal(m.store.get('vb_envio').tramite_id,'t-a');m.close();return 'Clic de otro formulario pone timestamp en el envío global anterior.';
	});
	await check('WR-07',async()=>{
		const page=item().replace('<body>','<body><a href="https://hdl.handle.net/20.500.14414/999999">Referencia ajena</a>');const m=mount({html:page,env:{tramite_id:'t-a',titulo:'Tesis ficticia A',timestamp:'2026-11-16T10:00:00'}});await m.advance();const p=m.calls.find(c=>c.method==='POST');assert.equal(p.body.handle,'https://hdl.handle.net/20.500.14414/999999');m.close();return 'Se reporta el primer enlace hdl global, aunque corresponda a una referencia ajena.';
	});
	await check('WR-08',async()=>{
		const m=mount({html:item(''),env:{tramite_id:'t-a',titulo:'Tesis ficticia A',timestamp:'2026-11-16T10:00:00'}});await m.advance();m.doc.querySelector('meta[name="citation_title"]').content='Tesis ficticia A';m.doc.body.append(m.doc.createElement('span'));await m.advance(1000);assert.equal(m.calls.filter(c=>c.method==='POST').length,0);m.close();return 'Handle marcado visto antes de validar: el título que llega después no permite reportar, aun con otra mutación DOM.';
	});
	await check('WR-09',async()=>{
		const m=mount();await m.advance();m.doc.querySelector('form').remove();m.w.history.pushState({},'','/home');await m.advance();assert.ok(m.doc.querySelector('#vb-boton'));m.setReply(envelope('t-b','Tesis ficticia B'));m.doc.querySelector('#vb-boton').click();await m.advance();assert.equal(m.store.get('vb_envio').tramite_id,'t-b');m.close();return 'Botón persiste fuera del formulario y registra un nuevo envío aunque no haya controles.';
	});
	await check('WR-10',async()=>{
		const m=mount();await m.advance();assert.ok(m.calls[0].options.ontimeout===undefined);assert.ok(m.calls[0].options.timeout===undefined);m.close();return 'Peticiones GM sin plazo ni manejador timeout; inspección de las opciones emitidas, no simulación de red real.';
	});
	await check('WR-11',async()=>{
		const m=mount({reply:envelope('t-a','')});await m.advance();assert.ok(m.store.get('vb_envio'));assert.equal(m.store.get('vb_envio').titulo,null);m.close();return 'Ficha sin título modifica otros campos y se registra como envío, pero no podrá reportar el depósito.';
	});
	await check('WR-12',async()=>{
		const bad=envelope();bad.ficha.extraidos[0].valor=['Título como lista'];assert.throws(()=>mount({reply:bad}),/trim/);return 'Título como lista válido para el DTO genérico hace fallar el wrapper antes de crear el botón.';
	});
	fs.writeFileSync(path.join(__dirname,'resultados.json'),JSON.stringify({base:'c9e5499',scope:'Offline; DOM/GM simulados; no ejecuta el servidor ni la aplicación Angular completa',cases:result},null,2)+'\n');
	console.log(JSON.stringify({cases:result.length,reproduced:result.length,results:result},null,2));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
