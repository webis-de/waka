import {KgVis} from "./kg-vis.js";
import mustache from "https://cdnjs.cloudflare.com/ajax/libs/mustache.js/4.2.0/mustache.js";

window.addEventListener("DOMContentLoaded", main)

let kgVis = null
const entityCache = new Map()

function main(){
    let kgButton = document.getElementById("create-kg-button")
    kgButton.addEventListener("click", onKgButtonClicked)

    let overlayCloseButton = document.getElementById("overlay-close")
    overlayCloseButton.addEventListener("click", function (){
        let overlay = document.getElementById("overlay")
        overlay.style.display = "none"
    })

    let overlay = document.getElementById("overlay")
    overlay.addEventListener("click", function (e) {
        let target = e.target
        let containerElems = document.querySelectorAll(".overlay-entity-container ." + target.className)

        if(containerElems.length > 0){
            if(target.className !== "overlay-entity-container"){
                target = containerElems[0].closest(".overlay-entity-container")
            }
        }

        if(target.className === "overlay-entity-container"){
            console.log(target)
            let currentEntityId = document.getElementById("overlay-content").href
            let clickedEntityId = target.getElementsByClassName("overlay-entity-link")[0].href

            let newNode = KgVis.createNodeFromEntity(entityCache.get(clickedEntityId))
            let oldNode = kgVis.getNodeById(currentEntityId)
            oldNode.label = newNode.label
            // kgVis.addNode(KgVis.createNodeFromEntity(entityCache.get(clickedEntityId)))
        }
    },false)

    addEventListener("keydown", function (e){
        if(e.key === "Escape"){
            let overlayCloseButton = document.getElementById("overlay-close")
            overlayCloseButton.dispatchEvent(new Event("click"))
        }
    })

    let textEditor = document.getElementById("text-editor")
    window.addEventListener("mouseup", function (e){
        let editor = document.getElementById("text-editor")
        let annToolbox = document.getElementById("ann-toolbox")
        let selection = window.getSelection()
        if(selection.type === "Range"){
            let range = selection.getRangeAt(0)
            let container = range.commonAncestorContainer
            if (editor.contains(container)){
                let clientRect = range.getBoundingClientRect()
                annToolbox.style.top = (clientRect.top - 22) + "px"
                annToolbox.style.left = clientRect.left + "px"
                annToolbox.style.visibility = "visible"
            }
        } else{
            annToolbox.style.visibility = "hidden"
        }
    })
}

function onKgButtonClicked(e){
    let kgButton = e.target
    kgButton.disabled = true

    let loadingRing = document.getElementById("loading-ring")
    loadingRing.classList.remove("hidden")
    loadingRing.classList.add("visible")

    let editor = document.getElementById("text-editor")
    // editor.setAttribute("contenteditable", false)

    let editorContent = editor.innerText
    editorContent = editorContent.trim()
    editorContent = editorContent.replaceAll(/[\s\n]+/g, " ")

    let postData = {"content": editorContent}

    requestBackend("POST","/api/v1/kg", null, null, postData, onKgReceive)
    // onKgReceive(JSON.stringify(debugKG()))
}

function onKgReceive(responseText){
    let kgButton = document.getElementById("create-kg-button")


    let loadingRing = document.getElementById("loading-ring")
    loadingRing.classList.remove("visible")
    loadingRing.classList.add("hidden")

    let kg = JSON.parse(responseText)
    console.log(kg)

    let entities =  Array.from(kg.entities)
    entities.sort(function (a, b){return +(a.start_idx - b.start_idx) || -((a.end_idx - a.start_idx) - (b.end_idx - b.start_idx))})
    let textEditor = document.getElementById("text-editor")

    let idx = 0

    textEditor.innerHTML = ""
    for(let entity of entities){
        if (entity.start_idx < idx){
            continue
        }

        let plain = kg.text.substring(idx, entity.start_idx)
        if(plain !== ""){
            let textNode = document.createTextNode(plain)
            textEditor.appendChild(textNode)
        }

        textEditor.appendChild(createEntitySpan(entity))
        idx = entity.end_idx
    }

    let textNode = document.createTextNode(kg.text.substring(idx))
    textEditor.appendChild(textNode)

    kgVis = new KgVis(kg)
    kgVis.draw(document.getElementById("kg-vis"))
}

function onEntitySearchReceive(responseText){
    let data = JSON.parse(responseText)["data"]

    entityCache.clear()
    for (let entity of data){
        entityCache.set(entity.id, entity)
    }

    let entityResultContainer = document.getElementById("overlay-entity-result-container")
    entityResultContainer.innerHTML = ""

    fetch("/static/templates/entity-change.mustache")
        .then((response) => response.text())
        .then((template) => {
            entityResultContainer.innerHTML = mustache.render(template, {"entities": data})
        }).then(() => {
            let entityId = document.getElementById("overlay-content").href
            let radio = entityResultContainer.querySelectorAll(".overlay-entity-selection[value=\"" + entityId + "\"]")
            if (radio.length > 0){
                radio[0].checked = true
            }
        })
}

function createEntitySpan(entity){
    let entitySpan = document.createElement("span")
    entitySpan.innerText = entity.text
    entitySpan.classList.add("entity")
    entitySpan.setAttribute("href", entity.url)

    entitySpan.appendChild(createEntityDescription(entity))

    entitySpan.addEventListener("click", function (e){
        drawEntityChangePanel(e.target)
    })

    entitySpan.addEventListener("mouseover", function (e){
        if (kgVis !== null){
            let node = kgVis.getNodeById(e.target.getAttribute("href"))
            node.color = getComputedStyle(document.documentElement).getPropertyValue("--highlight-color")
            kgVis.addNode(node)
        }
    })

    entitySpan.addEventListener("mouseout", function (e){
        if (kgVis !== null){
            let node = kgVis.getNodeById(e.target.getAttribute("href"))
            node.color = getComputedStyle(document.documentElement).getPropertyValue("--default-color")
            kgVis.addNode(node)
        }
    })

    return entitySpan
}

export function createEntityDescription(entity){
    let entityDescription = document.createElement("div")
    entityDescription.classList.add("entity-description")
    entityDescription.setAttribute("contenteditable", false)

    let header = document.createElement("header")
    header.innerText = entity.label
    entityDescription.appendChild(header)

    entityDescription.appendChild(document.createElement("hr"))

    let description = document.createElement("div")
    description.innerText = entity.description
    entityDescription.appendChild(description)

    let link = document.createElement("a")
    link.href = entity.url ? entity.url : entity.id
    link.target = "_blank"
    link.innerText = entity.url
    entityDescription.appendChild(link)

    entityDescription.addEventListener("click", function (e){
        e.stopPropagation()
    })

    return entityDescription
}

function drawEntityChangePanel(entitySpan){
    let overlay = document.getElementById("overlay")
    overlay.style.display = "flex"

    let overlayContent = document.getElementById("overlay-content")
    overlayContent.href = entitySpan.getAttribute("href")

    let entityName = [].reduce.call(entitySpan.childNodes, function(a, b) { return a + (b.nodeType === 3 ? b.textContent : ''); }, '');

    let overlayEntityHeading = document.getElementById("overlay-entity-heading")
    overlayEntityHeading.innerText = entityName

    let entityResultContainer = document.getElementById("overlay-entity-result-container")
    entityResultContainer.innerHTML = ""

    requestBackend(
        "GET", "https://metareal-kb.web.webis.de/api/v1/kb/entity/search",
        {"q": entityName}, null, null,
        onEntitySearchReceive)
}

function requestBackend(method, url, params, header, data, callback){
    let request = new XMLHttpRequest()
    request.addEventListener("readystatechange", function () {
        genericCallback(this, callback)
    })

    request.open(method, url + formatParams(params), true)
    request.setRequestHeader("Content-Type", "application/json")
    request.setRequestHeader("Accept", "application/json")
    if(method === "POST"){
        request.send(JSON.stringify(data))
    } else{
        request.send()
    }
}

function genericCallback(req, callback){
    if(req.readyState === 4){
        if (req.status === 200){
            callback(req.responseText)
        }
    }
}

function formatParams( params ){
    if (params === null){
        return "";
    }

    return "?" + Object
        .keys(params)
        .map(function(key){
            return key+"="+encodeURIComponent(params[key])
        })
        .join("&")
}

function debugKG() {
    return {
        text: "The Bauhaus-Universität Weimar is a university located in Weimar, Germany.",
        entities: [
            {
                    url: "http://www.wikidata.org/entity/Q573975",
                    start_idx: 4,
                    end_idx: 30,
                    text: "Bauhaus-Universität Weimar",
                    label: "Bauhaus-University Weimar",
                    score: 1.0,
                    description: "university"
            },
            {
                    url: "http://www.wikidata.org/entity/Q3955",
                    start_idx: 58,
                    end_idx: 64,
                    text: "Weimar",
                    label: "Weimar",
                    score: 1.0,
                    description: "city in the federal state of Thuringia, Germany"
            },
            {
                    url: "http://www.wikidata.org/entity/Q183",
                    start_idx: 66,
                    end_idx: 73,
                    text: "Germany",
                    label: "Germany",
                    score: 1.0,
                    description: "country in Central Europe"
            }
        ],
        triples: [
            {
                subject: {
                    url: "http://www.wikidata.org/entity/Q573975",
                    start_idx: 4,
                    end_idx: 30,
                    text: "Bauhaus-Universität Weimar",
                    label: "Bauhaus-University Weimar",
                    score: 1.0,
                    description: "university"
                },
                predicate: {
                    url: "http://www.wikidata.org/prop/direct/P131",
                    text: "located in the administrative territorial entity",
                    label: "located in the administrative territorial entity",
                    description: "the item is located on the territory of the following administrative entity. Use P276 for specifying locations that are non-administrative places and for items about events. Use P1382 if the item falls only partially into the administrative entity."
                },
                object: {
                    url: "http://www.wikidata.org/entity/Q3955",
                    start_idx: 58,
                    end_idx: 64,
                    text: "Weimar",
                    label: "Weimar",
                    score: 1.0,
                    description: "city in the federal state of Thuringia, Germany"
                }
            },
            {
                subject: {
                    url: "http://www.wikidata.org/entity/Q573975",
                    start_idx: 4,
                    end_idx: 30,
                    text: "Bauhaus-Universität Weimar",
                    label: "Bauhaus-University Weimar",
                    score: 1.0,
                    description: "university"
                },
                predicate: {
                    url: "http://www.wikidata.org/prop/direct/P17",
                    text: "country",
                    label: "country",
                    description: "sovereign state that this item is in (not to be used for human beings)"
                },
                object: {
                    url: "http://www.wikidata.org/entity/Q183",
                    start_idx: 66,
                    end_idx: 73,
                    text: "Germany",
                    label: "Germany",
                    score: 1.0,
                    description: "country in Central Europe"
                }
            },
            {
                subject: {
                    url: "http://www.wikidata.org/entity/Q3955",
                    start_idx: 58,
                    end_idx: 64,
                    text: "Weimar",
                    label: "Weimar",
                    score: 1.0,
                    description: "city in the federal state of Thuringia, Germany"
                },
                predicate: {
                    url: "http://www.wikidata.org/prop/direct/P17",
                    text: "country",
                    label: "country",
                    description: "sovereign state that this item is in (not to be used for human beings)"
                },
                object: {
                    url: "http://www.wikidata.org/entity/Q183",
                    start_idx: 66,
                    end_idx: 73,
                    text: "Germany",
                    label: "Germany",
                    score: 1.0,
                    description: "country in Central Europe"
                }
            },
        ]
    }
}