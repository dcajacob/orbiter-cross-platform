-- Camera tour for the stock "In low orbit over Africa" scenario.
-- Keep the vessel and simulation running while one Earth-fixed observer
-- descends over the sunlit Americas towards Kennedy's runway.
local rad = math.pi / 180
local start = oapi.get_simtime()
oapi.set_cameraaperture(25 * rad)
local function ease(x)
    x = math.min(1, math.max(0, x))
    return x*x*(3-2*x)
end
repeat
    local t = oapi.get_simtime() - start
    local travel = ease((t-3)/13)
    local descent = ease((t-3)/35)
    local approach = ease((t-23)/15)
    local altitude = 21000000 * math.exp(math.log(900/21000000) * descent)
    oapi.set_cameramode({mode='ground', ref='Earth',
        lng=-86 + (-80.681 + 86)*travel, lat=16 + (28.596-16)*travel,
        alt=altitude, alt_above_ground=0, phi=(90+30*approach)*rad,
        tht=(-90+45*approach)*rad})
    proc.skip()
until t >= 42
oapi.write_log('Vulkan Earth descent complete')
