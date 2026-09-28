-- Original, bounded rules for the five optional LUCINET plant models.
local R = {version=1, maxEntries=128, range=1500, originRange=4000, cooldown=6, effectSeconds=4}
local models = {
    ['meshes/lucinet/plant0.dae']='crystal', ['meshes/lucinet/plant1.dae']='crystal',
    ['meshes/lucinet/tree0.dae']='tree', ['meshes/lucinet/tree1.dae']='tree',
    ['meshes/lucinet/tree2.dae']='tree',
}
function R.model(path)
    if type(path) ~= 'string' then return nil end
    local normalized=path:lower():gsub('\\','/')
    if normalized:sub(1,7) ~= 'meshes/' then normalized='meshes/'..normalized end
    if not models[normalized] then return nil end
    return normalized,models[normalized]
end
function R.finite(n)
    return type(n)=='number' and n==n and n~=math.huge and n~=-math.huge
end
function R.integer(n,lo,hi)
    return R.finite(n) and n%1==0 and n>=lo and n<=hi
end
function R.text(s)
    return type(s)=='string' and #s>0 and #s<=256 and not s:find('[%z\1-\31]')
end
function R.cellKey(cell)
    if not cell then return nil end
    if cell.isExterior then
        return tostring(cell.worldSpaceId or '')..':'..tostring(cell.gridX)..':'..tostring(cell.gridY)
    end
    return tostring(cell.id)
end
function R.copy(entry)
    if not entry then return nil end
    local result={}
    for key,value in pairs(entry) do result[key]=value end
    return result
end
function R.validEntry(key,e)
    if type(e)~='table' or not R.text(key) or key~=e.id then return false end
    local expected={id=true,recordId=true,model=true,cell=true,kind=true,stage=true,
        visits=true,firstDay=true,lastDay=true}
    for field in pairs(e) do if not expected[field] then return false end end
    local model,kind=R.model(e.model)
    return R.text(e.recordId) and R.text(e.cell) and model==e.model and kind==e.kind
        and R.integer(e.stage,1,3) and R.integer(e.visits,1,1000000)
        and R.integer(e.firstDay,0,100000000) and R.integer(e.lastDay,e.firstDay,100000000)
end
function R.reply(entry,action,previousStage,previousDay,today,sun,storm)
    local name=entry.kind=='tree' and 'Der leuchtende Baum' or 'Der Kristall'
    if action=='answer' then
        if previousStage==1 then
            return name..' nimmt deinen Gruß auf. Ein Lichtkreis antwortet. »Ich werde mich an diesen Ort mit dir erinnern.«'
        end
        return name..' antwortet auf deinen Gruß mit einem ruhigen Lichtkreis. »Du musst nichts beweisen. Bleib einen Augenblick.«'
    end
    if previousStage==2 and today>previousDay then
        return name..' erkennt deinen Schritt wieder. »Ein anderer Tag. Derselbe Gruß.« Das Leuchten findet zu einem gemeinsamen Rhythmus.'
    end
    if previousStage==0 then
        return name..' antwortet auf deine Aufmerksamkeit. »Du hörst zu. Das genügt für den Anfang.«'
    end
    if storm then return name..' trägt den Sturm im Licht. »Auch wenn es laut wird, bleibt ein stiller Platz.«' end
    if sun and sun<0.2 then return name..' leuchtet leise in der Dunkelheit. »Ich habe deinen letzten Besuch behalten.«' end
    if entry.stage==3 then return name..' lässt einen vertrauten Lichtkreis aufsteigen. »Du kennst den Weg zurück.«' end
    return name..' antwortet mit einem einzelnen Lichtkreis. »Vielleicht gibst du mir eines Tages einen Gruß zurück.«'
end
return R
