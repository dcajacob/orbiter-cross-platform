"use strict";
const element = id => document.getElementById(id);
const page = element("page");
let mode = "contents";
const known = new Set(helpBook.pages.map(p => p.topic));
function safeTopic(topic) {
    const path = topic.split("#")[0];
    return known.has(path) ? topic : helpBook.default;
}
function show(topic) {
    topic = safeTopic(topic);
    page.src = topic;
}
function render() {
    element("query-label").hidden = mode === "contents";
    const words = element("query").value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    let entries;
    if (mode === "search") {
        entries = words.length ? helpBook.pages.filter(p => words.every(w => (p.title+" "+p.text).toLocaleLowerCase().includes(w))) : [];
    } else {
        entries = helpBook[mode].length ? helpBook[mode] : helpBook.pages;
        if (mode === "index") entries = entries.filter(p => words.every(w => p.title.toLocaleLowerCase().includes(w)));
    }
    element("topics").replaceChildren();
    for (const item of entries) {
        const li = document.createElement("li");
        li.style.paddingLeft = (mode === "contents" ? (item.depth || 0)*14 : 0)+"px";
        if (item.topic) {
            const a = document.createElement("a");
            a.textContent = item.title; a.href = "?topic="+encodeURIComponent(item.topic);
            a.addEventListener("click", event => { event.preventDefault(); show(item.topic); });
            li.append(a);
        } else li.textContent = item.title;
        element("topics").append(li);
    }
    element("status").textContent = mode === "search" && !words.length ? "Enter words to search this book." : entries.length+" topics";
}
for (const name of ["contents", "index", "search"]) {
    element(name).addEventListener("click", () => {
        mode = name;
        for (const id of ["contents", "index", "search"]) element(id).setAttribute("aria-pressed", String(id === name));
        element("query").value = ""; render();
        if (name !== "contents") element("query").focus();
    });
}
element("query").addEventListener("input", render);
element("home").addEventListener("click", () => show(helpBook.default));
element("back").addEventListener("click", () => history.back());
element("forward").addEventListener("click", () => history.forward());
element("title").textContent = helpBook.title;
document.title = helpBook.title;
for (const name of ["vessel", "scenario"]) {
    const value = new URLSearchParams(location.search).get(name);
    if (value) {
        try {
            const url = new URL(value);
            if (url.protocol === "file:" && url.pathname.endsWith("/_viewer.html")) {
                element(name).href = url.href; element(name).hidden = false;
            }
        } catch (_) { /* Invalid optional context does not hide the requested topic. */ }
    }
}
show(new URLSearchParams(location.search).get("topic") || helpBook.default);
render();
