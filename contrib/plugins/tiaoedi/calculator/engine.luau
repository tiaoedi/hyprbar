-- Self-contained bounded arithmetic parser: no evaluation, processes or network.
local M = {}
function M.evaluate(input, answer)
  if type(input) ~= "string" or #input == 0 or #input > 512 then return nil, "Digite uma expressão de até 512 caracteres." end
  local function parse()
    local text = input:gsub(",", "."):gsub("×", "*"):gsub("÷", "/"):gsub("−", "-")
    local pos, token, number, count, depth = 1, "", nil, 0, 0
    local function nextToken()
      while text:sub(pos,pos):match("%s") do pos = pos + 1 end
      count = count + 1
      if count > 256 then error("Expressão muito longa.", 0) end
      local rest = text:sub(pos)
      local numeric = rest:match("^%d+%.?%d*[eE][+-]?%d+") or rest:match("^%.%d+[eE][+-]?%d+") or rest:match("^%d+%.?%d*") or rest:match("^%.%d+")
      if numeric then
        token = "number"; number = tonumber(numeric); pos = pos + #numeric
      elseif rest:match("^%a") then
        token = rest:match("^%a+"):lower(); pos = pos + #token
        if token ~= "sqrt" and token ~= "pi" and token ~= "ans" then error("Função desconhecida.", 0) end
      else
        token = text:sub(pos,pos); pos = pos + 1
        if token ~= "" and not token:match("^[+*/()%%^%-]$") then error("Caractere inválido.", 0) end
      end
    end
    local expression, signedPower
    local function atom()
      depth = depth + 1
      if depth > 32 then error("Parênteses demais.", 0) end
      local value
      if token == "number" then value = number; nextToken()
      elseif token == "pi" then value = math.pi; nextToken()
      elseif token == "ans" then value = tonumber(answer) or 0; nextToken()
      elseif token == "sqrt" then
        nextToken()
        if token ~= "(" then error("Use sqrt(número).", 0) end
        nextToken(); value = expression()
        if token ~= ")" then error("Falta fechar parênteses.", 0) end
        if value < 0 then error("Raiz de número negativo.", 0) end
        value = math.sqrt(value); nextToken()
      elseif token == "(" then
        nextToken(); value = expression()
        if token ~= ")" then error("Falta fechar parênteses.", 0) end
        nextToken()
      else error("Número ou parênteses esperado.", 0) end
      depth = depth - 1
      return value
    end
    local function power()
      local value = atom()
      if token == "^" then
        nextToken(); value = value ^ signedPower()
        return value, true
      end
      return value, false
    end
    signedPower = function()
      if token == "+" or token == "-" then
        local op = token; nextToken(); local value, powered = signedPower()
        return op == "-" and -value or value, powered
      end
      return power()
    end
    local function percentageUnit()
      local value, powered = signedPower()
      if token ~= "%" then return value, false, false end
      value = value / 100; nextToken()
      if token == "%" or token == "^" then error("Operador inválido após porcentagem.", 0) end
      -- Preserve the observed additive-rate and chained-rate semantics without
      -- applying a relative rate across an explicit parenthesis boundary.
      local followed = token == "+" or token == "-" or token == "*" or token == "/"
      return value, not powered, followed
    end
    local function product()
      local value, relative, followed = percentageUnit()
      while token == "*" or token == "/" do
        local op = token; nextToken(); local right = percentageUnit()
        if op == "/" and right == 0 then error("Não é possível dividir por zero.", 0) end
        if op == "*" then value = value * right else value = value / right end
      end
      return value, relative, followed
    end
    expression = function()
      local value = product()
      while token == "+" or token == "-" do
        local op = token; nextToken(); local right, relative, followed = product()
        if relative then right = value * (followed and right / 100 or right) end
        if op == "+" then value = value + right else value = value - right end
      end
      return value
    end
    nextToken(); local value = expression()
    if token ~= "" then error("Expressão incompleta ou operador ausente.", 0) end
    return value
  end
  local ok, result = pcall(parse)
  if ok then
    if result ~= result or result == math.huge or result == -math.huge then return nil, "Resultado fora do intervalo real." end
    return result
  end
  return nil, tostring(result)
end
return M
