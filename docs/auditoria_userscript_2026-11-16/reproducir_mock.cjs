// Ejecuta solo el HTML del mock local, con fetch sustituido y sin cargar recursos.
// No ejecuta los bundles de UNT, abre servidores ni envía solicitudes de red.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=process.env.VISTOBUENO_AUDIT_ROOT || path.resolve(__dirname,'../..');
const {JSDOM}=require(require.resolve('jsdom',{paths:[path.join(root,'tools/dspace-fill')]}));
(async()=>{
	const results=[];
	for(const page of ['submit','item']) {
		const payload='<img src=x onerror="window.__auditXss=1">';
		const requests=[];
		const source=fs.readFileSync(path.join(root,'tools/dspace-fill/dev/mock-dspace',page+'.html'),'utf8');
		const d=new JSDOM(source,{
			url:'http://localhost:18081/mock/'+page,
			runScripts:'dangerously',
			beforeParse(w){
				w.setTimeout=(fn)=>setTimeout(fn,0);
				w.fetch=async url=>{
					requests.push(String(url));
					return {status:200,json:async()=>page==='submit'?{tramite_id:'t-ficticio',ficha:{extraidos:[{campo:'dc.title',valor:payload}]}}:{handle:'https://hdl.handle.net/20.500.14414/900001',timestamp:'2026-11-16T10:00:00',titulo_observado:payload}};
				};
			}
		});
		await new Promise(resolve=>setTimeout(resolve,20));
		const injected=d.window.document.querySelector('img[onerror]');
		assert.ok(injected,page);
		injected.dispatchEvent(new d.window.Event('error'));
		assert.equal(d.window.__auditXss,1,page);
		results.push({page,injectedMarkup:true,handlerExecuted:true,network:'fetch simulado; recursos externos no habilitados',mockedRequests:requests});
		d.window.close();
	}
	fs.writeFileSync(path.join(__dirname,'resultado_mock.json'),JSON.stringify(results,null,2)+'\n');
	console.log(JSON.stringify(results,null,2));
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
