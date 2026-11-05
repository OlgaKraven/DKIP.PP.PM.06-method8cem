"""Prepare independent operation fixtures; no previous cohort's application is used."""
from pathlib import Path
import json,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1]
APP='''using System.Globalization;
using System.Text.Json;
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.UseDefaultFiles(); app.UseStaticFiles();
var gate = new object();
void Log(string kind, object detail) { lock(gate) File.AppendAllText("events.jsonl", JsonSerializer.Serialize(new { at=DateTimeOffset.UtcNow, kind, detail })+Environment.NewLine); }
List<Entry> Read() => JsonSerializer.Deserialize<List<Entry>>(File.ReadAllText("data.json"), new JsonSerializerOptions { PropertyNameCaseInsensitive=true }) ?? throw new InvalidDataException("Empty data");
app.MapGet("/api/context", () => Results.Text(File.ReadAllText("context.json"), "application/json"));
app.MapGet("/api/records", (HttpRequest request) => {
    var sw=System.Diagnostics.Stopwatch.StartNew();
    var text=request.Query["end"].ToString();
    DateOnly end=default;
    if(request.Query.Keys.Any(k=>k!="end") || request.Query["end"].Count>1 || (request.Query.ContainsKey("end") && !DateOnly.TryParseExact(text,"yyyy-MM-dd",CultureInfo.InvariantCulture,DateTimeStyles.None,out end))) {
        Log("request",new { path=request.Path.Value, query=request.QueryString.Value,status=400,ms=sw.Elapsed.TotalMilliseconds });
        return Results.Json(new { error="end must be one date YYYY-MM-DD" },statusCode:400);
    }
    try {
        var all=Read();
        // The contract includes every record on the final date.
        var result=all.Where(e=>text=="" || DateOnly.ParseExact(e.Date,"yyyy-MM-dd",CultureInfo.InvariantCulture) < end).OrderBy(e=>e.Id).ToList();
        Log("request",new { path=request.Path.Value, query=request.QueryString.Value,status=200,ms=sw.Elapsed.TotalMilliseconds,ids=result.Select(e=>e.Id) });
        return Results.Json(result);
    } catch(Exception e) when(e is IOException or JsonException or FormatException or InvalidDataException) {
        Log("request",new { path=request.Path.Value, query=request.QueryString.Value,status=500,ms=sw.Elapsed.TotalMilliseconds,error=e.GetType().Name });
        return Results.Json(new { error="data_unavailable" },statusCode:500);
    }
});
app.MapGet("/health", () => { try { Read(); return Results.Json(new { status="ok" }); } catch(Exception e) { Log("health_error",new { error=e.GetType().Name }); return Results.Json(new {status="unavailable"},statusCode:503); } });
app.MapPost("/ops/event/{kind}", (string kind) => {
    if(!new[]{"detected","acknowledged","change_started","restored","confirmed"}.Contains(kind)) return Results.BadRequest();
    Log(kind,new { note="Local training event" });return Results.Json(new{recorded=kind});
});
app.MapGet("/ops/events", () => Results.Text(File.Exists("events.jsonl")?File.ReadAllText("events.jsonl"):"", "text/plain"));
Log("started",new{process=Environment.ProcessId});
app.Run();
record Entry(int Id,string Title,string Date);
'''
UI='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Пульт сопровождения</title><style>body{font:18px/1.5 Arial;max-width:900px;margin:35px auto;padding:0 20px;color:#20232b}h1{font-size:30px}section{padding:20px;background:#f4f4f6;margin:20px 0;border-radius:10px}button,input{font:inherit;padding:8px;margin:5px}pre{background:white;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:16px;border:1px solid #ccc}a{color:#1549a0}label{display:block}</style><h1>Пульт сопровождения</h1><p id="context"></p><section><h2>Запрос к работающей системе</h2><label>Конечная дата включительно (YYYY-MM-DD): <input id="end" placeholder="Оставить пустым для всех записей"></label><button id="send">Отправить запрос</button><button id="health">Проверить готовность</button><pre id="out">Запрос ещё не отправлен</pre></section><section><h2>Журнал работы</h2><p>Регистрировать события в момент действия. Кнопки сохраняют фактическое UTC-время.</p><button data-event="detected">Инцидент обнаружен</button><button data-event="acknowledged">Работа принята</button><button data-event="change_started">Изменение начато</button><button data-event="restored">Работа восстановлена</button><button data-event="confirmed">Результат подтверждён</button><p id="event"></p><a href="/ops/events" target="_blank">Открыть журнал событий</a></section><script>let out=document.querySelector('#out');async function query(path){let r=await fetch(path);let text=await r.text();out.textContent='GET '+path+'\\nHTTP '+r.status+'\\n'+text;}document.querySelector('#send').onclick=()=>query('/api/records'+(document.querySelector('#end').value?'?end='+encodeURIComponent(document.querySelector('#end').value):''));document.querySelector('#health').onclick=()=>query('/health');document.querySelectorAll('[data-event]').forEach(b=>b.onclick=async()=>{let r=await fetch('/ops/event/'+b.dataset.event,{method:'POST'});document.querySelector('#event').textContent=await r.text();});fetch('/api/context').then(r=>r.json()).then(c=>document.querySelector('#context').textContent='Вариант '+c.variant+' — '+c.domain+'. Контрольная дата: '+c.end+'. Исходные ID: '+c.ids.join(', '));</script></html>'''
CHECK='''"""HTTP regression collection. Run: py -3 check.py URL cases.json"""
import json,sys,urllib.request,urllib.error
base=sys.argv[1].rstrip('/')
cases=json.load(open(sys.argv[2],encoding='utf-8-sig'))
failed=0
for c in cases:
    try:
        r=urllib.request.urlopen(base+c['path']);status=r.status;data=json.load(r)
    except urllib.error.HTTPError as e:status=e.code;data=json.load(e)
    ok=status==c['status'] and (('ids' not in c) or isinstance(data,list) and [x['id'] for x in data]==c['ids'])
    if 'error' in c:ok=ok and data.get('error')==c['error']
    print(('PASS' if ok else 'FAIL'),c['name'],status,json.dumps(data,ensure_ascii=False));failed+=not ok
print('FAILED',failed,'OF',len(cases));sys.exit(bool(failed))
'''
def pack(folder,target):
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file() and not any(x in p.parts for x in ('bin','obj')):z.write(p,p.relative_to(folder).as_posix())
def build():
    domains=[x[2:].strip() for x in (ROOT/'docs/domain.md').read_text(encoding='utf-8').splitlines() if x.startswith('* ')]
    (ROOT/'downloads').mkdir(exist_ok=True)
    contexts=[]
    for n,domain in enumerate(domains,1):
        folder=ROOT/f'variants/v{n:02}';(folder/'wwwroot').mkdir(parents=True,exist_ok=True)
        day=3+(n%20);end=f'2027-03-{day:02}';ids=[n*100+i for i in (1,2,3)]
        context=dict(variant=f'{n:02}',domain=domain,end=end,ids=ids,reaction_minutes=15 if n%2 else 30,recovery_minutes=60 if n%3 else 90)
        data=[dict(id=i,title=f'{domain} — запись {j}',date=f'2027-03-{day+j-2:02}') for j,i in enumerate(ids,1)]
        cases=[dict(name='All records',path='/api/records',status=200,ids=ids),dict(name='Before all records',path=f'/api/records?end=2027-03-{day-2:02}',status=200,ids=[]),dict(name='After all records',path=f'/api/records?end=2027-03-{day+2:02}',status=200,ids=ids),dict(name='Invalid date',path='/api/records?end=bad',status=400,error='end must be one date YYYY-MM-DD')]
        for name,value in [('context.json',context),('data.json',data),('baseline.cases.json',cases)]:(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (folder/'Program.cs').write_text(APP,encoding='utf-8');(folder/'wwwroot/index.html').write_text(UI,encoding='utf-8')
        (folder/'Operations.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk.Web"><PropertyGroup><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup></Project>',encoding='utf-8')
        (folder/'.gitignore').write_text('bin/\nobj/\nevents.jsonl\n',encoding='utf-8')
        (folder/'README.md').write_text(f'# Стенд варианта {n:02}\n\n{domain}\n\n.NET SDK 10, Python 3 для отдельного тестового проекта.\nРаспаковать в свою рабочую папку. Открыть PowerShell в ней: `dotnet run --urls http://127.0.0.1:5186`. Открыть тот же адрес в браузере.\nИсходные данные: data.json; контроль: context.json; действующий контракт: contract.md.\nПорядок диагностики, изменения и восстановления — в методических рекомендациях.\n',encoding='utf-8')
        (folder/'contract.md').write_text('# Действующий контракт\n\nGET /api/records без параметров: 200, все записи по id.\nПараметр end: одна дата YYYY-MM-DD; записи с date меньше либо равной end.\nПоля: id (целое), title (строка), date (YYYY-MM-DD).\nНет совпадений: 200 и []. Ошибочная дата, пустой/повторный end или неизвестный параметр: 400 JSON.\nНедоступный/невалидный файл данных: 500, {"error":"data_unavailable"}.\nGET /health: 200 с status=ok при читаемых данных; 503 при отказе данных.\nИзменение контракта в этой работе не требуется.\n',encoding='utf-8')
        pack(folder,ROOT/f'downloads/v{n:02}.zip');contexts.append(context)
    folder=ROOT/'test-project';folder.mkdir(exist_ok=True)
    (folder/'check.py').write_text(CHECK,encoding='utf-8')
    (folder/'README.md').write_text('# Отдельный тестовый проект\n\nPython 3, без дополнительных пакетов. Скопировать baseline.cases.json своего стенда как cases.json.\nИз папки тестового проекта: `py -3 check.py http://127.0.0.1:5186 cases.json`.\nДля нового случая добавить объект с name, path, status и ids (ожидаемые id).\nСохранять вывод до и после исправления. Обязательный граничный случай описан в методичке и карточке варианта.\n',encoding='utf-8')
    pack(folder,ROOT/'downloads/test-project.zip')
    (ROOT/'variants.json').write_text(json.dumps(contexts,ensure_ascii=False,indent=2),encoding='utf-8')
    print(len(contexts),'independent stands prepared')
if __name__=='__main__':build()
