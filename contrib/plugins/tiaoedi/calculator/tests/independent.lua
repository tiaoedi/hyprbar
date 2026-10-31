local root=arg[1] or "."
local engine=dofile(root.."/engine.luau")
local cases={
 {"100+10%",110},{"100-10%",90},{"100*10%",10},{"100/10%",1000},{"10%",0.1},
 {"200+10%+10%",220.22},{"100+10%*2",100.2},{"100+2*10%",100.2},
 {"(100+20)+10%",132},{"100+(10%)",100.1},{"100+(-10%)",99.9},{"100+-10%",90},
 {"100-(-10%)",100.1},{"100+10%%",false},{"100+(10+5)%",115},{"100+10%+5",105.1},
 {"100+5+10%",115.5},{"100+sqrt(100)%",110},{"100+10%^2",false},{"100+10%/2",100.05},
 {"100+50%*10%",100.05},{"100+2^3%",100.08},{"200+10%+5",205.2},{"(100+10%)",110},
 {"(200+10%)",220},{"100+10%-5",95.1},{"100+10%*2+1",101.2},{"200+10%*2",200.4},
 {"200+2*10%",200.2},{"100+10%/2+5",105.05},{"(100+10%)*2",220},{"2^3%",0.08},
 {"2^-2%",0.0025},{"100-10%+5",104.9},{"100-10%*2",99.8},{"100+10%*2^2",100.4},
 {"100+2*10%+10%",110.22},{"10%+100%",0.2},{"100+pi%",103.141592654},{"(100+10%+5)",105.1},
}
for _,case in ipairs(cases) do
 local value,err=engine.evaluate(case[1])
 if case[2]==false then assert(value==nil and err,"invalid expression accepted: "..case[1])
 else assert(value and math.abs(value-case[2])<0.00000001,case[1]..": expected "..tostring(case[2])..", got "..tostring(value)) end
end
assert(engine.evaluate("ans+10%",110)==121)
print("PASS independent percentage engine matches 40 recorded reference cases and plugin Ans")
local snapshot
local h={state={get=function() end,set=function() end,watch=function() end},
 commandExists=function() error("no external dependency probe allowed") end,
 runAsync=function() error("no external process allowed") end,
 pluginDataDir=function() return "/mock" end,json={encode=function(v) return v end},
 writeFile=function(_,v) snapshot=v; return true end}
local ui=setmetatable({}, {__index=function() return function(p,c) return {props=p,children=c} end end})
local env=setmetatable({hyprbar=h,ui=ui,panel={render=function() end}}, {__index=_G})
env.require=function(p) return dofile(root.."/"..p) end
assert(loadfile(root.."/panel.luau","t",env))(); env.onOpen()
for _,case in ipairs({{"100+10%","110"},{"100-10%","90"},{"100*10%","10"},{"100/10%","1000"}}) do
 env.onIpc("evaluate",case[1]); env.onIpc("diagnostics","")
 assert(snapshot.result==case[2] and snapshot.error=="" and not snapshot.pending,"panel did not calculate independently")
end
print("PASS native panel calculates percentages synchronously without commands or installed calculator")
