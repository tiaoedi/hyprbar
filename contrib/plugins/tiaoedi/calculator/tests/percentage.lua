-- Local percentage regression. External solver is deliberately not used.
local root=arg[1] or "."
local calc=dofile(root.."/engine.luau")
for _,case in ipairs({{"100+10%",110},{"100-10%",90},{"100*10%",10},{"100/10%",1000},{"100-200%",-100},{"1,5+10%",1.65}}) do
 local value=calc.evaluate(case[1])
 assert(value and math.abs(value-case[2])<0.000000001,case[1])
end
assert(calc.evaluate("ans+10%",110)==121)
assert(calc.evaluate("100+10%%")==nil)
assert(calc.evaluate("100+10%^2")==nil)
print("PASS local percentage increase discount multiplication division signs decimal and invalid syntax")
