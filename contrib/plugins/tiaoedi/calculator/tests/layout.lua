-- Regression: a full history must not expand the calculator's surface.
-- HOST MOCK tree checks; native screenshots are verified separately.
local root=arg[1] or "."
local tree,diagnostic,fixture
local ui=setmetatable({}, {__index=function(_,kind) return function(props,children) return {kind=kind,props=props,children=children} end end})
local h={state={set=function() end},pluginDataDir=function() return "/mock" end,
 json={encode=function(v) return v end,decode=function() return fixture end},
 writeFile=function(_,value) diagnostic=value; return true end}
local env=setmetatable({hyprbar=h,ui=ui,panel={render=function(t) tree=t end}}, {__index=_G})
env.require=function(path) return dofile(root.."/"..path) end
assert(loadfile(root.."/panel.luau","t",env))(); env.onOpen()
local function scan(node,rows,buttons)
 if node.props.key and node.props.key:match("^history%-%d+") then rows[#rows+1]=node end
 if node.kind=="button" and type(node.props.onClick)=="string" then buttons[node.props.onClick]=node.props end
 assert(node.kind~="scroll","unbounded runtime history must use bounded pages, not the failing scroll surface")
 for _,child in ipairs(node.children or {}) do scan(child,rows,buttons) end
end
for i=1,25 do env.onIpc("evaluate",tostring(i).."*2") end
local rows,buttons={},{}
-- Assert the actual failure first: the old tree contains twenty history rows.
local function countHistory(node)
 local n=(node.props.key and node.props.key:match("^history%-%d+")) and 1 or 0
 for _,child in ipairs(node.children or {}) do n=n+countHistory(child) end
 return n
end
assert(countHistory(tree)<=2,"history overflow: more than two rows rendered in the calculator")
scan(tree,rows,buttons)
assert(#rows==2 and buttons.previousPage and buttons.nextPage)
assert(not buttons.previousPage.enabled and buttons.nextPage.enabled)
assert(rows[1].props.text=="25*2 = 50")
for _=1,20 do env.nextPage() end
rows,buttons={},{}; scan(tree,rows,buttons)
assert(#rows==2 and not buttons.nextPage.enabled and buttons.previousPage.enabled)
assert(rows[2].props.text=="6*2 = 12")
env.previousPage(); rows,buttons={},{}; scan(tree,rows,buttons); assert(#rows==2)
print("PASS full history stays bounded to two rows with clamped page navigation")
fixture={expression="",result="0",answer=120,history={{expression="10*12",result="120"},{expression="10/12",result="0.833333333333"}}}
env.onIpc("restore-session","snapshot")
env.onIpc("diagnostics","")
assert(#diagnostic.history==2 and diagnostic.history[1].expression=="10*12" and diagnostic.answer==120,"existing user session was not preserved")
fixture={expression="bad",result="bad",history={}}
env.onIpc("restore-session","bad snapshot"); env.onIpc("diagnostics","")
assert(diagnostic.result=="0" and #diagnostic.history==2,"invalid session replaced user data")
print("PASS bounded session handoff preserves user history and answer during layout update")
