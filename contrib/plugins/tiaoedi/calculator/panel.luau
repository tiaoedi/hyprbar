local engine = require("./engine.luau")
local expression, result, answer, problem = "", "0", 0, ""
local opened, revision, completed = false, 0, false
local history = {}
local historyPage, pageSize = 1, 2

local keys = {
  {"AC", "⌫", "(", ")"},
  {"%", "√", "x²", "÷"},
  {"7", "8", "9", "×"},
  {"4", "5", "6", "−"},
  {"1", "2", "3", "+"},
  {"±", "0", ",", "="},
}
local function render()
  if not opened then return end
  local rows = {
    ui.label({text="hyprcalculadora",fontSize=22,fontWeight="bold"}),
    ui.input({key="expression-"..tostring(revision),value=expression,placeholder="Digite uma conta…",fontSize=22,controlSize="lg",focus=true,onChange="onExpressionChanged",onSubmit="calculate"}),
    ui.label({text=result,fontSize=30,fontWeight="bold",color="primary",maxLines=2}),
    ui.label({text=problem,fontSize=12,color="error",maxLines=2,height=30}),
  }
  for _, line in ipairs(keys) do
    local buttons = {}
    for _, key in ipairs(line) do
      local value=key
      buttons[#buttons+1]=ui.button({key="key-"..value,text=value,controlSize="sm",flexGrow=1,variant=value=="=" and "primary" or "default",onClick=function() pushKey(value) end})
    end
    rows[#rows+1]=ui.row({gap=6},buttons)
  end
  rows[#rows+1]=ui.row({gap=6}, {
    ui.button({text="Ans",controlSize="sm",flexGrow=1,onClick=function() pushKey("ans") end}),
    ui.button({text="π",controlSize="sm",flexGrow=1,onClick=function() pushKey("pi") end}),
    ui.button({text="Copiar",glyph="copy",controlSize="sm",flexGrow=2,onClick="copyResult",enabled=problem==""}),
  })
  rows[#rows+1]=ui.row({gap=8,align="center"},{
    ui.label({text="Histórico da sessão",flexGrow=1,fontWeight="bold"}),
    ui.button({text="Limpar histórico",controlSize="sm",variant="ghost",onClick="clearHistory"}),
  })
  local historyRows={}
  local pageCount=math.max(1,math.ceil(#history/pageSize))
  historyPage=math.max(1,math.min(historyPage,pageCount))
  local first=(historyPage-1)*pageSize+1
  for index=first,math.min(#history,first+pageSize-1) do
    local item=history[index]
    local saved=item
    historyRows[#historyRows+1]=ui.button({key="history-"..index,text=saved.expression.." = "..saved.result,controlSize="sm",contentAlign="start",onClick=function()
      expression=saved.result; result=saved.result; answer=tonumber(saved.result) or answer
      problem=""; completed=false; revision=revision+1; render()
    end})
  end
  if #historyRows==0 then historyRows[1]=ui.label({text="As últimas 20 contas ficam aqui.",fontSize=12}) end
  rows[#rows+1]=ui.column({gap=4},historyRows)
  rows[#rows+1]=ui.row({gap=6,align="center"},{
    ui.button({text="Mais recentes",controlSize="sm",onClick="previousPage",enabled=historyPage>1,flexGrow=1}),
    ui.label({text=tostring(historyPage).." / "..tostring(pageCount),fontSize=12}),
    ui.button({text="Mais antigas",controlSize="sm",onClick="nextPage",enabled=historyPage<pageCount,flexGrow=1}),
  })
  rows[#rows+1]=ui.label({text="Enter calcula • vírgula ou ponto decimal • porcentagem automática",fontSize=12,maxLines=2})
  panel.render(ui.column({padding=12,gap=8},rows))
end
function onExpressionChanged(text)
  expression = tostring(text):sub(1,513); completed=false; problem=""
end
local function commit(value)
  answer=value
  result=string.format("%.12g",value==0 and 0 or value)
  problem=""; completed=true
  table.insert(history,1,{expression=expression,result=result})
  while #history>20 do table.remove(history) end
  historyPage=1
  hyprbar.state.set("latest",result)
  render()
end
function calculate(text)
  if type(text)=="string" then onExpressionChanged(text); revision=revision+1 end
  local value,err=engine.evaluate(expression,answer)
  if value==nil then problem=err; render(); return end
  commit(value)
end
function pushKey(key)
  if key=="=" then calculate(); return end
  if key=="AC" then expression=""; result="0"; problem=""; completed=false
  elseif key=="⌫" then expression=expression:gsub("[^\128-\191][\128-\191]*$", ""); problem=""; completed=false
  elseif key=="±" then expression=expression=="" and "-" or ("-("..expression..")"); completed=false
  else
    local token=({["×"]="*",["÷"]="/",["−"]="-",[","]=".",["√"]="sqrt(",["x²"]="^2"})[key] or key
    if completed then
      local continuation=token=="+" or token=="-" or token=="*" or token=="/" or token=="^2" or token=="%"
      expression=continuation and result or ""
    end
    expression=(expression..token):sub(1,513); problem=""; completed=false
  end
  revision=revision+1; render()
end
function copyResult()
  if problem=="" and not hyprbar.copyToClipboard(result,"text/plain") then problem="Não foi possível copiar."; render() end
end
function previousPage() historyPage=math.max(1,historyPage-1); render() end
function nextPage() historyPage=math.min(math.max(1,math.ceil(#history/pageSize)),historyPage+1); render() end
function clearHistory() history={}; historyPage=1; render() end
local function restoreSession(payload)
  if type(payload)~="string" or #payload>16000 then return end
  local saved=hyprbar.json.decode(payload)
  if type(saved)~="table" or type(saved.expression)~="string" or #saved.expression>512
    or type(saved.result)~="string" or #saved.result>32 or type(saved.history)~="table" or #saved.history>20 then return end
  local value=tonumber(saved.result)
  if not value or value~=value or value==math.huge or value==-math.huge then return end
  local restored={}
  for _,item in ipairs(saved.history) do
    if type(item)~="table" or type(item.expression)~="string" or #item.expression>512 or type(item.result)~="string" or #item.result>32 then return end
    local n=tonumber(item.result)
    if not n or n~=n or n==math.huge or n==-math.huge then return end
    restored[#restored+1]={expression=item.expression,result=item.result}
  end
  local last=tonumber(saved.answer) or value
  if last~=last or last==math.huge or last==-math.huge then return end
  expression=saved.expression; result=saved.result; answer=last; history=restored
  problem=type(saved.error)=="string" and saved.error:sub(1,256) or ""
  completed=false; historyPage=1; revision=revision+1
  hyprbar.state.set("latest",result); render()
end
function onIpc(event,payload)
  if event=="evaluate" then calculate(payload)
  elseif event=="clear" then pushKey("AC")
  elseif event=="clear-history" then clearHistory()
  elseif event=="history-next" then nextPage()
  elseif event=="history-previous" then previousPage()
  elseif event=="restore-session" then restoreSession(payload)
  elseif event=="diagnostics" then
    local dir=hyprbar.pluginDataDir()
    if dir then hyprbar.writeFile(dir.."/diagnostics.json",hyprbar.json.encode({expression=expression,result=result,answer=answer,error=problem,history=history,historyPage=historyPage,pageSize=pageSize,pending=false})) end
  end
end
function onOpen(_context) opened=true; render() end
function onClose() opened=false end
