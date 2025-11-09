--[[
Splash Lua script that waits for a specific element to appear.
More robust than simple time.sleep() calls.
]]--

function main(splash, args)
    splash:init_cookies(splash.args.cookies)
    assert(splash:go(args.url))

    -- Wait for a specific CSS selector to appear
    local selector = args.wait_selector or '.content-loaded'

    local element_loaded = splash:call_later(function()
        local element = splash:select(selector)
        return element ~= nil
    end)

    -- Poll for element with timeout
    local timeout = args.timeout or 10
    local start_time = splash:get_perf_stats().walltime

    while not element_loaded() do
        local elapsed = splash:get_perf_stats().walltime - start_time
        if elapsed > timeout then
            splash:set_result_status_code(408)  -- Request Timeout
            return {
                error = 'Element not found: ' .. selector,
                html = splash:html()
            }
        end
        assert(splash:wait(0.1))
    end

    return {
        html = splash:html(),
        cookies = splash:get_cookies(),
    }
end
