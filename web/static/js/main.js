import {KgVis} from "./kg-vis.js";

window.addEventListener("DOMContentLoaded", main)

function main(){
    let kgButton = document.getElementById("create-kg-button")
    kgButton.addEventListener("click", onKgButtonClicked)

    let overlayCloseButton = document.getElementById("overlay-close")
    overlayCloseButton.addEventListener("click", function (){
        let overlay = document.getElementById("overlay")
        overlay.style.display = "none"
    })

    addEventListener("keydown", function (e){
        if(e.key === "Escape"){
            let overlayCloseButton = document.getElementById("overlay-close")
            overlayCloseButton.dispatchEvent(new Event("click"))
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
    let editorContent = editor.innerText
    editorContent = editorContent.trim()
    editorContent = editorContent.replaceAll(/[\s\n]+/g, " ")

    let postData = {"content": editorContent}

    // requestBackend("POST","/api/v1/kg", null, null, postData, onKgReceive)
    onKgReceive("{\n" +
        "  \"text\": \"The Bauhaus-Universität Weimar is a university located in Weimar, Germany.\",\n" +
        "  \"entities\": [],\n" +
        "  \"triples\": [\n" +
        "    {\n" +
        "      \"subject\": {\n" +
        "        \"url\": \"http://www.wikidata.org/entity/Q573975\",\n" +
        "        \"start_idx\": 4,\n" +
        "        \"end_idx\": 30,\n" +
        "        \"text\": \"Bauhaus-Universität Weimar\"\n" +
        "      },\n" +
        "      \"predicate\": {\n" +
        "        \"url\": \"http://www.wikidata.org/prop/direct/P131\",\n" +
        "        \"text\": \"located in the administrative territorial entity\"\n" +
        "      },\n" +
        "      \"object\": {\n" +
        "        \"url\": \"http://www.wikidata.org/entity/Q3955\",\n" +
        "        \"start_idx\": 58,\n" +
        "        \"end_idx\": 64,\n" +
        "        \"text\": \"Weimar\"\n" +
        "      }\n" +
        "    },\n" +
        "    {\n" +
        "      \"subject\": {\n" +
        "        \"url\": \"http://www.wikidata.org/entity/Q573975\",\n" +
        "        \"start_idx\": 4,\n" +
        "        \"end_idx\": 30,\n" +
        "        \"text\": \"Bauhaus-Universität Weimar\"\n" +
        "      },\n" +
        "      \"predicate\": {\n" +
        "        \"url\": \"http://www.wikidata.org/prop/direct/P17\",\n" +
        "        \"text\": \"country\"\n" +
        "      },\n" +
        "      \"object\": {\n" +
        "        \"url\": \"http://www.wikidata.org/entity/Q183\",\n" +
        "        \"start_idx\": 66,\n" +
        "        \"end_idx\": 73,\n" +
        "        \"text\": \"Germany\"\n" +
        "      }\n" +
        "    },\n" +
        "    {\n" +
        "      \"subject\": {\n" +
        "        \"url\": \"http://www.wikidata.org/entity/Q3955\",\n" +
        "        \"start_idx\": 58,\n" +
        "        \"end_idx\": 64,\n" +
        "        \"text\": \"Weimar\"\n" +
        "      },\n" +
        "      \"predicate\": {\n" +
        "        \"url\": \"http://www.wikidata.org/prop/direct/P17\",\n" +
        "        \"text\": \"country\"\n" +
        "      },\n" +
        "      \"object\": {\n" +
        "        \"url\": \"http://www.wikidata.org/entity/Q183\",\n" +
        "        \"start_idx\": 66,\n" +
        "        \"end_idx\": 73,\n" +
        "        \"text\": \"Germany\"\n" +
        "      }\n" +
        "    }\n" +
        "  ]\n" +
        "}")
}

function onKgReceive(responseText){
    let kgButton = document.getElementById("create-kg-button")
    kgButton.disabled = false

    let loadingRing = document.getElementById("loading-ring")
    loadingRing.classList.remove("visible")
    loadingRing.classList.add("hidden")

    let kg = JSON.parse(responseText)
    console.log(kg)

    let entities =  Array.from(kg.entities)
    entities.sort(function (a, b){return a.start_idx - b.start_idx})
    let textEditor = document.getElementById("text-editor")

    let idx = 0

    textEditor.innerHTML = ""
    for(let entity of entities){
        let plain = kg.text.substring(idx, entity.start_idx)
        if(plain !== ""){
            let textNode = document.createTextNode(plain)
            textEditor.appendChild(textNode)
        }

        textEditor.appendChild(createDOMElementFromEntity(entity))
        idx = entity.end_idx
    }

    let textNode = document.createTextNode(kg.text.substring(idx))
    textEditor.appendChild(textNode)

    let kgVis = new KgVis(kg)
    kgVis.draw(document.getElementById("kg-vis"))
}

function createDOMElementFromEntity(entity){
    let entitySpan = document.createElement("span")
    entitySpan.innerText = entity.text
    entitySpan.classList.add("entity")
    entitySpan.setAttribute("href", entity.url)

    let entityDescription = document.createElement("span")
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
    link.href = entity.url
    link.target = "_blank"
    link.innerText = entity.url
    entityDescription.appendChild(link)

    entitySpan.appendChild(entityDescription)

    // entitySpan.addEventListener("dblclick", function (e){
    //     window.open(e.target.getAttribute("href"), "_blank").focus()
    // })

    entitySpan.addEventListener("click", function (e){
        drawEntityChangePanel(e.target)
    })

    entityDescription.addEventListener("click", function (e){
        e.stopPropagation()
    })

    return entitySpan
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
        function (responseText) {
            let data = JSON.parse(responseText)["data"]

            for (let i in data){
                let entityId = document.getElementById("overlay-content").href
                let entityContainer = document.createElement("div")
                entityContainer.className = "overlay-entity-container"
                entityResultContainer.appendChild(entityContainer)

                let entitySelection = document.createElement("input")
                entitySelection.className = "overlay-entity-selection"
                entitySelection.type = "radio"
                entitySelection.name = "entity"
                entitySelection.value = data[i]["id"]

                if(entityId === data[i]["id"]){
                    entitySelection.checked = true;
                }
                entitySelection.addEventListener("change", function(e){
                    let radio = e.target
                    let entityId = document.getElementById("overlay-content").href
                    let entitySpans = document.querySelectorAll(".entity[href=\""+ entityId + "\"]")
                    for (let entitySpan of entitySpans){
                        console.log(entitySpan)
                        entitySpan.setAttribute("href", radio.value)
                        entitySpan.getElementsByClassName("entity-description")[0].innerText = radio.value
                    }
                })
                entityContainer.appendChild(entitySelection)

                let entity = document.createElement("div")
                entity.className = "overlay-entity"
                entityContainer.appendChild(entity)

                let entityLabel = document.createElement("h2")
                entityLabel.className = "overlay-entity-label"
                entityLabel.innerText = data[i]["label"]
                entity.appendChild(entityLabel)

                let entityLink = document.createElement("a")
                entityLink.className = "overlay-entity-link"
                entityLink.href = data[i]["id"]
                entityLink.innerText = data[i]["id"]
                entityLink.target = "_blank"
                entity.appendChild(entityLink)

                let entityDescription = document.createElement("div")
                entityDescription.className = "overlay-entity-description"
                entityDescription.innerText = data[i]["description"]
                entity.appendChild(entityDescription)

                let entityFreq = document.createElement("div")
                entityFreq.className = "overlay-entity-freq"
                entityFreq.innerText = "Frequency: " + data[i]["frequency"]
                entity.appendChild(entityFreq)
            }
        })
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