// Exercise the delivered file:// help in an actual Chromium browser.
const {chromium} = require(process.env.ORBITER_PLAYWRIGHT_MODULE || 'playwright-core');
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const assert = require('assert');
const crypto = require('crypto');
const args = process.argv.slice(2);
const single = args[0] === '--request';
const source = args[1];
const out = path.resolve(args[2]);
fs.mkdirSync(out, {recursive:true});
(async () => {
    const browser = await chromium.launch({executablePath:process.env.ORBITER_HELP_BROWSER || '/opt/google/chrome/chrome', headless:true});
    try {
        const page = await browser.newPage({viewport:{width:1280,height:900}});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const requests = [];
        // Desktop file handlers can receive either a file URL or an absolute
        // path. Convert only the transport; never reconstruct a topic/context.
        if (single) requests.push(path.isAbsolute(source) ? pathToFileURL(source).href : source);
        else {
            for (const line of fs.readFileSync(path.join(source, 'Help/catalog.tsv'), 'utf8').trim().split('\n')) {
                const [key, viewer, topic] = line.split('\t');
                if (key.startsWith('html/')) requests.push(pathToFileURL(path.join(source,viewer)).href+'?topic='+encodeURIComponent(topic));
            }
        }
        const results = [];
        for (const url of requests) {
            await page.goto(url);
            const frame = page.frameLocator('#page');
            await frame.locator('body').waitFor();
            const actualUrl = page.url();
            const topic = new URL(actualUrl).searchParams.get('topic');
            assert(topic, 'Desktop launch lost the requested help topic');
            const text = await frame.locator('body').innerText();
            // Atlantis' original landing page is only a heading and one link.
            assert(text.trim().length > 20, 'Original topic body did not load: '+url);
            const frameUrl = await page.locator('#page').getAttribute('src');
            assert.equal(frameUrl, topic, 'Requested help topic silently changed');
            const brokenImages = await frame.locator('img').evaluateAll(imgs => imgs.filter(i => !i.complete || !i.naturalWidth).map(i => i.src));
            assert.deepEqual(brokenImages, [], 'Missing original topic images');
            if (single) {
                const id=crypto.createHash('sha256').update(url).digest('hex').slice(0,16);
                await page.screenshot({path:path.join(out,id+'.png')});
                fs.writeFileSync(path.join(out,id+'.json'), JSON.stringify({url:actualUrl,launch_url:url,topic,body:text.slice(0,250),errors},null,2));
            }
            results.push({topic, title:await page.title(), images:await frame.locator('img').count()});
        }
        if (!single) {
            const root = pathToFileURL(path.join(source,'Help/books/orbiter/_viewer.html')).href;
            await page.goto(root+'?topic=mainmenu.htm');
            await page.locator('#search').click();
            await page.locator('#query').fill('playback editor');
            const links = page.locator('#topics a');
            assert(await links.count()>0, 'Full-text search returned no original recorder documentation');
            await links.filter({hasText:/playback event editor/i}).first().click();
            await page.frameLocator('#page').locator('body').waitFor();
            assert((await page.frameLocator('#page').locator('body').innerText()).includes('Playback event editor'));
            await page.screenshot({path:path.join(out,'search.png')});
            await page.locator('#index').click();
            await page.locator('#query').fill('camera');
            assert(await page.locator('#topics a').count()>0, 'Original keyword index missing');
            await page.locator('#contents').click();
            await page.locator('#topics a').filter({hasText:/^Introduction$/}).click();
            await page.frameLocator('#page').locator('h1').filter({hasText:'Introduction'}).waitFor();
            await page.locator('#topics a').filter({hasText:/^Main menu$/}).click();
            await page.frameLocator('#page').locator('h1').filter({hasText:'Main menu'}).waitFor();
            await page.locator('#back').click();
            await page.frameLocator('#page').locator('h1').filter({hasText:'Introduction'}).waitFor();
            await page.locator('#forward').click();
            await page.frameLocator('#page').locator('h1').filter({hasText:'Main menu'}).waitFor();
            await page.screenshot({path:path.join(out,'main-menu.png')});
            await page.goto(root+'?topic=mfd_sync.htm');
            await page.frameLocator('#page').getByRole('link',{name:'Align Orbital Planes MFD'}).click();
            await page.waitForURL(/topic=mfd_align.htm/);
            assert((await page.frameLocator('#page').locator('body').innerText()).includes('Align'));
            const dg = pathToFileURL(path.join(source,'Help/books/vessels/deltaglider/_viewer.html')).href;
            await page.goto(dg+'?topic=deltaglider.htm');
            await page.frameLocator('#page').getByRole('link',{name:'Lua interface extensions'}).click();
            await page.frameLocator('#page').getByRole('heading',{name:'Class DeltaGlider'}).waitFor();
            await page.screenshot({path:path.join(out,'delta-glider-lua.png')});
            const vessel = dg+'?topic=deltaglider.htm';
            const scenario = pathToFileURL(path.join(source,'Help/books/scenarios/default/checklists/quickstart/_viewer.html')).href+'?topic=quickstart.htm';
            await page.goto(root+'?topic=mainmenu.htm&vessel='+encodeURIComponent(vessel)+'&scenario='+encodeURIComponent(scenario));
            await page.locator('#scenario').click(); await page.waitForURL(scenario);
            await page.goto(root+'?topic=mainmenu.htm&vessel='+encodeURIComponent(vessel));
            await page.locator('#vessel').click(); await page.waitForURL(vessel);
        }
        assert.deepEqual(errors, [], 'Help JavaScript errors');
        if(!single) fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({status:'passed',books:results,search:true,index:true,contents:true,history:true,cross_book_links:true,generated_lua:true,context_buttons:true,errors},null,2)+'\n');
        console.log('Browser help checks passed:', results.length, 'topics');
    } finally {await browser.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
