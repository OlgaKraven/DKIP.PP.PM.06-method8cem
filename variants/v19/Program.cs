using System.Globalization;
using System.Text.Json;
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.UseDefaultFiles(); app.UseStaticFiles();
var gate = new object();
void Log(string kind, object detail) { lock(gate) File.AppendAllText("events.jsonl", JsonSerializer.Serialize(new { at=DateTimeOffset.UtcNow, kind, detail })+Environment.NewLine); }
List<Entry> Read() {
    var entries=JsonSerializer.Deserialize<List<Entry>>(File.ReadAllText("data.json"), new JsonSerializerOptions { PropertyNameCaseInsensitive=true }) ?? throw new InvalidDataException("Empty data");
    if(entries.Any(e=>e is null || e.Id<=0 || e.Title is null || !DateOnly.TryParseExact(e.Date,"yyyy-MM-dd",CultureInfo.InvariantCulture,DateTimeStyles.None,out _)) || entries.Select(e=>e.Id).Distinct().Count()!=entries.Count) throw new InvalidDataException("Invalid record schema");
    return entries;
}
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
