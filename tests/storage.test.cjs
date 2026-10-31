// 실제 data.enc를 읽지 않고 브라우저 저장 경계를 합성 자료로 검사한다.
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const html = fs.readFileSync(require('node:path').join(__dirname, '..', 'index.html'), 'utf8');
const source = html.split('<script>')[1].split("document.getElementById('f').onsubmit")[0];
function fixture() {
  const data = new Map();
  const localStorage = {getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v)};
  const context = vm.createContext({crypto:webcrypto,TextEncoder,TextDecoder,URL,atob,btoa,localStorage,sessionStorage:{removeItem(){}}});
  vm.runInContext(source + '\npassword="synthetic-only";globalThis.api={encrypt,decrypt,validateEdits,payload,persist,getOverlay:()=>overlay};',context);
  return {api:context.api,data,localStorage};
}
const place = {id:'synthetic-1',name:'합성 식당',area:'테스트',kind:'테스트',status:'가고 싶음',menu:'',note:'합성 비공개 메모',minutes:45,date:'2026-01-01T12:00',lat:null,lon:null,link:''};
test('암호화 저장·복호화·변조·오류 비밀번호 및 저장 실패 보존',async()=>{
  const {api,data,localStorage}=fixture();
  await api.persist({[place.id]:place});
  const stored=data.get('date-map-edits-v1');
  assert(!stored.includes(place.note));assert(!stored.includes(place.name));
  const restored=await api.decrypt(JSON.parse(stored),'synthetic-only');
  assert.equal(api.validateEdits(restored)[place.id].note,place.note);
  await assert.rejects(()=>api.decrypt(JSON.parse(stored),'wrong'));
  const corrupt=JSON.parse(stored);corrupt.ct=(corrupt.ct[0]==='A'?'B':'A')+corrupt.ct.slice(1);
  await assert.rejects(()=>api.decrypt(corrupt,'synthetic-only'));
  localStorage.setItem=()=>{throw new Error('QuotaExceededError')};
  await assert.rejects(()=>api.persist({[place.id]:{...place,note:'저장 실패'}}));
  assert.equal(data.get('date-map-edits-v1'),stored);
  assert.equal(api.getOverlay()[place.id].note,place.note);
});
test('다른 탭의 변경분을 덮어쓰지 않는다',async()=>{
  const {api,data}=fixture();await api.persist({[place.id]:place});
  data.set('date-map-edits-v1','another-tab');
  await assert.rejects(()=>api.persist({[place.id]:place}),/다른 탭/);
  assert.equal(data.get('date-map-edits-v1'),'another-tab');
});
test('백업 입력: 좌표 쌍·범위·음수 시간·위험 링크·중복 식별자 거부',()=>{
  const {api}=fixture();
  for(const patch of [{lat:37},{lat:91,lon:127},{minutes:-1},{link:'javascript:alert(1)'},{name:''}]){
    assert.throws(()=>api.validateEdits(api.payload({a:{...place,...patch}})));
  }
  assert.throws(()=>api.validateEdits({format:'date-map-edits',version:1,places:[place,place]}));
  assert.equal(api.validateEdits(api.payload({a:place}))[place.id].lat,null);
});
