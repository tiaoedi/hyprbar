-- Visible branding regression; actual dependency identifiers remain truthful.
local root=arg[1] or "."
local tree,tip
local ui=setmetatable({}, {__index=function(_,kind) return function(props,children) return {kind=kind,props=props,children=children} end end})
local h={state={get=function() end,set=function() end,watch=function() end},commandExists=function() return false end}
local env=setmetatable({hyprbar=h,ui=ui,panel={render=function(v) tree=v end}}, {__index=_G})
env.require=function(p) return dofile(root.."/"..p) end
assert(loadfile(root.."/panel.luau","t",env))(); env.onOpen()
local function inspect(node)
 for _,key in ipairs({"text","tooltip","placeholder"}) do
  local value=node.props[key]
  if type(value)=="string" then assert(not value:lower():find("gnome",1,true),"old brand visible in "..key) end
 end
 for _,child in ipairs(node.children or {}) do inspect(child) end
end
assert(tree.children[1].props.text=="hyprcalculadora","panel title was not renamed")
inspect(tree)
env.onIpc("evaluate","100+10%")
inspect(tree)
local w=setmetatable({hyprbar=h,barWidget={setGlyph=function() end,setText=function() end,setTooltip=function(v) tip=v end}}, {__index=_G})
assert(loadfile(root.."/widget.luau","t",w))()
assert(tip:find("hyprcalculadora",1,true) and not tip:lower():find("gnome",1,true))
print("PASS hyprcalculadora title tooltip help and errors contain only the requested visible branding")
