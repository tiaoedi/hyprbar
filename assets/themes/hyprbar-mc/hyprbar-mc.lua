-- hyprbar-mc: compositor-side geometry, shadows and frosted shell surfaces.
-- Does not change monitors, bindings, layout, app launchers or window opacity.
local M = {}
function M.apply()
    hl.config({
        general = {
            gaps_in = 2,
            gaps_out = 2,
            border_size = 1,
            col = {
                active_border = "rgba(ffffff88)",
                inactive_border = "rgba(7a7a8033)",
            },
        },
        decoration = {
            rounding = 14,
            shadow = {
                enabled = true,
                range = 28,
                render_power = 3,
                color = "rgba(00000040)",
                color_inactive = "rgba(00000024)",
            },
            blur = {
                enabled = true,
                size = 6,
                passes = 2,
            },
        },
    })
    hl.layer_rule({
        name = "hyprbar-mc-frosted-glass",
        match = { namespace = "(hyprbar|noctalia)-(bar.*|dock.*|panel.*|notification.*|osd.*)" },
        blur = true,
        ignore_alpha = 0.05,
    })
end
return M
