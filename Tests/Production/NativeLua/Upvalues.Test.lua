-- Licensed under the MIT License
-- Empty lists, shared open/closed upvalues, retained closures and collection.
local function capture(x)
    return function() return x end
end
assert(capture(17)() == 17)

local function shared()
    local a, b = 0, 100
    return function() a = a + 1; return a end,
           function() b = b - 1; return b end,
           function() return a + b end
end
local inc, dec, total = shared()
for i = 1, 100 do
    assert(inc() == i)
    assert(dec() == 100 - i)
    assert(total() == 100)
    collectgarbage('collect')
end

local values = {}
for i = 1, 5000 do
    local value = i
    values[i] = function(delta) value = value + delta; return value end
end
collectgarbage('collect')
local sum = 0
for i = 1, 5000 do
    assert(values[i](0) == i)
    sum = sum + values[i](1)
end
assert(sum == 12507500)
values = nil
collectgarbage('collect')
print('upvalue-stress-ok', sum, total())
