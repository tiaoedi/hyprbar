-- HOST MOCK ONLY. Real entry code; this is not native UI verification.
local root = arg[1] or "."
local tree, closed, clipboard, state, files = nil, false, nil, {}, {}
local ui = setmetatable({}, {__index=function(_, kind) return function(props, children) return {kind=kind,props=props,children=children} end end})
local h = {
  state={get=function(k) return state[k] end,set=function(k,v) state[k]=v end,watch=function() end},
  copyToClipboard=function(text,mime) clipboard={text,mime}; return true end,
  pluginDataDir=function() return "/mock/calculator" end,
  writeFile=function(path,raw) files[path]=raw; return true end,
  json={encode=function(v) return v end},
}
local env=setmetatable({hyprbar=h,ui=ui,panel={render=function(t) tree=t end,close=function() closed=true end}}, {__index=_G})
env.require=function(path) return dofile(root.."/"..path) end
local fn=loadfile(root.."/panel.luau","t",env)
assert(fn,"painel da calculadora ainda não implementado")
fn(); env.onOpen()
local function hasText(node,text)
 if node.props.text==text then return true end
 for _,child in ipairs(node.children or {}) do if hasText(child,text) then return true end end
 return false
end
assert(type(env.onExpressionChanged)=="function" and type(env.calculate)=="function")
env.onExpressionChanged("2+3*4"); env.calculate()
assert(hasText(tree,"14"),"expression not evaluated/rendered")
assert(state.latest=="14","result not shared with widget")
print("PASS HOST MOCK keyboard input renders real parser result")
local function findButton(node,text)
 if node.kind=="button" and node.props.text==text then return node.props end
 for _,child in ipairs(node.children or {}) do local b=findButton(child,text); if b then return b end end
end
local function click(text)
 local b=findButton(tree,text); assert(b,"missing button "..text)
 local cb=b.onClick; if type(cb)=="string" then env[cb]() else assert(type(cb)=="function"); cb() end
end
click("AC"); click("7"); click("×"); click("6"); click("=")
assert(hasText(tree,"42"))
click("+"); click("1"); click("0"); click("="); assert(hasText(tree,"52"))
click("Copiar"); assert(clipboard[1]=="52" and clipboard[2]=="text/plain")
click("AC"); env.onExpressionChanged("1/0"); env.calculate()
assert(hasText(tree,"Não é possível dividir por zero."))
click("AC"); click("9"); click("⌫"); click("8"); click("="); assert(hasText(tree,"8"))
print("PASS HOST MOCK keypad, continuation, clipboard, backspace and errors")
assert(type(env.onIpc)=="function", "missing calculator IPC/history verification")
for i=1,25 do env.onIpc("evaluate",tostring(i).."*2") end
env.onIpc("diagnostics","")
local snapshot=files["/mock/calculator/diagnostics.json"]
assert(snapshot.result=="50" and #snapshot.history==20 and snapshot.error=="")
assert(findButton(tree,"25*2 = 50"),"history is not rendered")
click("25*2 = 50"); click("+"); click("2"); click("="); assert(hasText(tree,"52"))
click("Limpar histórico"); env.onIpc("diagnostics",""); assert(#files["/mock/calculator/diagnostics.json"].history==0)
print("PASS HOST MOCK bounded history, reuse, clear and explicit diagnostics")
local function inputKey(node)
 if node.kind=="input" then return node.props.key end
 for _,child in ipairs(node.children or {}) do local key=inputKey(child); if key then return key end end
end
local previousKey=inputKey(tree)
env.onIpc("evaluate","sqrt(81)")
assert(inputKey(tree)~=previousKey,"programmatic input must replace uncontrolled native field")
print("PASS HOST MOCK programmatic calculation refreshes native input identity")
local toggles,glyph,tip=0,nil,nil
h.togglePanel=function(id) assert(id=="tiaoedi/calculator:panel"); toggles=toggles+1 end
local w=setmetatable({hyprbar=h,barWidget={setGlyph=function(v) glyph=v end,setText=function() end,setTooltip=function(v) tip=v end}}, {__index=_G})
local wf=loadfile(root.."/widget.luau","t",w); assert(wf,"calculator widget missing"); wf(); w.onClick()
assert(glyph=="calculator" and toggles==1 and tip:find("hyprcalculadora",1,true))
print("PASS HOST MOCK calculator widget toggles correct native panel")
