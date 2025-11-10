--[[
Example Splash Lua script for handling complex interactions.
This script clicks a specifications tab and scrolls to trigger lazy-loaded content.
]]--

function main(splash, args)
    splash:init_cookies(splash.args.cookies)

    -- Navigate to URL
    assert(splash:go(args.url))
    assert(splash:wait(2))

    -- Click on a specific tab (e.g., "Specifications")
    local specs_tab = splash:select('#specifications-tab')
    if specs_tab then
        specs_tab:mouse_click()
        assert(splash:wait(1))
    end

    -- Scroll to trigger lazy-loaded content
    splash:set_viewport_full()
    for i = 1, 5 do
        splash:evaljs('window.scrollTo(0, document.body.scrollHeight)')
        assert(splash:wait(0.5))
    end

    -- Wait for a specific element to appear
    local loaded = splash:wait_for_resume([[
        function main(splash) {
            var checkExist = setInterval(function() {
                if (document.querySelector('.product-specifications')) {
                    clearInterval(checkExist);
                    splash.resume('Element loaded');
                }
            }, 100);

            setTimeout(function() {
                clearInterval(checkExist);
                splash.resume('Timeout');
            }, 10000);
        }
    ]], 15)

    return {
        html = splash:html(),
        cookies = splash:get_cookies(),
        png = splash:png(),  -- Optional: capture screenshot
    }
end
