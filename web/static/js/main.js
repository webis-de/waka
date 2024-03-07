import {KgVis} from "./kg-vis.js";
import mustache from "https://cdnjs.cloudflare.com/ajax/libs/mustache.js/4.2.0/mustache.js";

window.addEventListener("DOMContentLoaded", main)

let kgVis = null
let kg = null

const entityCache = new Map()

const exampleNS = "https://example.org/"
const wakaNS ="https://waka.webis.de/"
const rdfsNS = "http://www.w3.org/2000/01/rdf-schema#"
const schemaNS = "https://schema.org/"

function main(){
    $("#loading-icon").hide()

    let kgButton = document.getElementById("create-kg-button")
    kgButton.addEventListener("click", onKgButtonClicked)

    let overlayCloseButton = document.getElementById("overlay-close")
    overlayCloseButton.addEventListener("click", function (){
        let overlay = document.getElementById("overlay-entity")
        overlay.style.display = "none"
    })

    let overlay = document.getElementById("overlay-entity")
    overlay.addEventListener("click",  onClick)

    let saveButton = document.getElementById("save-button")
    saveButton.addEventListener("click", function (){
        download("kg.nt", convertToRDF(kg))
    })

    let addEntityButton = document.getElementById("add-annotation-button")
    addEntityButton.addEventListener("click", function (){
        let annToolbox = document.getElementById("ann-toolbox")
        annToolbox.style.visibility = "hidden"

        let selection = window.getSelection()
        if(selection.type === "Range"){
            let range = selection.getRangeAt(0)
            let container = range.commonAncestorContainer
            let text = container.textContent.substring(range.startOffset, range.endOffset)

            let entity = {
                text: text,
                url: exampleNS + encodeURIComponent(text),
                description: "literal",
                start_idx: range.startOffset,
                end_idx: range.endOffset
            }
            let entitySpan = createEntitySpan(entity)

            let currentHTML =  container.textContent

            if(kgVis === null){
                kgVis = new KgVis({triples: [], entities: []})
                kgVis.draw(document.getElementById("kg-vis"))
                kg = emptyKG()
            }

            kg.entities = kg.entities.concat([
                {
                    text: text,
                    url: exampleNS + encodeURIComponent(text),
                    description: "literal",
                    mentions: [entity]
                }
            ])

            kg.entity_mentions = kg.entity_mentions.concat([
                entity
            ])

            kgVis.update(kg)

            container.replaceWith(document.createTextNode(currentHTML.substring(0, range.startOffset)), entitySpan, document.createTextNode(currentHTML.substring(range.endOffset)))
            drawEntityChangePanel(entity)

            selection.removeAllRanges()
        }
    })

    let deleteEntityButton = document.getElementById("entity-delete")
    deleteEntityButton.addEventListener("click", function (){
        let overlayContent = document.getElementById("overlay-content")
        let oldEntity = JSON.parse(overlayContent.getAttribute("data-entity"))

        updateKG(oldEntity, null)
        kgVis.update(kg)

        if("mentions" in oldEntity){
            for(let mentions of oldEntity.mentions){
                let span = document.getElementById(mentions.start_idx + ":" + mentions.end_idx + ":" + mentions.url)
                span.replaceWith(document.createTextNode(mentions.text))
            }
        }else{
            let span = document.getElementById(oldEntity.start_idx + ":" + oldEntity.end_idx + ":" + oldEntity.url)
            span.replaceWith(document.createTextNode(oldEntity.text))
        }

        let overlay = document.getElementById("overlay-entity")
        overlay.style.display = "none"
    })

    let overlayEntitySearchBox = document.getElementById("overlay-entity-search-box")
    overlayEntitySearchBox.addEventListener("keypress", function (e){
        if(e.key === 'Enter'){
            let entityName = e.target.value
            requestBackend(
        "GET", "https://metareal-kb.web.webis.de/api/v1/kb/entity/search",
        {"q": entityName}, null, null,
        function (responseText) {onEntitySearchReceive(responseText, entityName)})
            e.target.value = ""
        }
    })

    let example1Anchor = document.getElementById("example-1")
    example1Anchor.addEventListener("click", function (){
        let editor = document.getElementById("text-editor")
        editor.innerText =
            "Dracula Untold is a 2014 American dark fantasy action film directed by Gary Shore in his feature film debut and written by Matt Sazama and Burk Sharpless. " +
            "A reboot of the \"Dracula\" film series, the plot creates an origin story for the titular character, rather than using the storyline of Bram Stoker's 1897 novel. " +
            "In this adaptation, Dracula is the monster alter ego of historical figure Vlad III \"the Impaler\" Drăculea. " +
            "Luke Evans portrays the title character, with Sarah Gadon, Dominic Cooper, Art Parkinson, and Charles Dance cast in supporting roles. Principal photography began in Northern Ireland on August 5, 2013."
    })

    let example2Anchor = document.getElementById("example-2")
    example2Anchor.addEventListener("click", function () {
        let editor = document.getElementById("text-editor")
        editor.innerText =
            "The Bauhaus-Universität Weimar is a university located in Weimar, Germany, and specializes in the artistic and technical fields. " +
            "Established in 1860 as the Great Ducal Saxon Art School, it gained collegiate status on 3 June 1910. In 1919 the school was renamed Bauhaus by its new director Walter Gropius and it received its present name in 1996. " +
            "There are more than 4000 students enrolled, with the percentage of international students above the national average at around 27%. In 2010 the Bauhaus-Universität Weimar commemorated its 150th anniversary as an art school and college in Weimar."
    })

    addEventListener("keydown", function (e){
        if(e.key === "Escape"){
            let overlayCloseButton = document.getElementById("overlay-close")
            overlayCloseButton.dispatchEvent(new Event("click"))
        }
    })

    addEventListener("mouseup", function (e){
        let editor = document.getElementById("text-editor")
        let annToolbox = document.getElementById("ann-toolbox")
        let selection = window.getSelection()
        if(selection.type === "Range"){
            let range = selection.getRangeAt(0)
            let container = range.commonAncestorContainer
            if (editor.contains(container)){
                let clientRect = range.getBoundingClientRect()

                annToolbox.style.top = (clientRect.top - 32) + "px"
                annToolbox.style.left = clientRect.left + "px"
                annToolbox.style.visibility = "visible"
            }
        } else{
            annToolbox.style.visibility = "hidden"
        }
    })


}

function onClick(e) {
    let target = e.target

    if(target.className === ""){
        return;
    }
    let containerElems = document.querySelectorAll(".overlay-entity-container ." + target.className)

    if(containerElems.length > 0){
        if(target.className !== "overlay-entity-container"){
            target = containerElems[0].closest(".overlay-entity-container")
        }
    }

    if(target.className === "overlay-entity-container"){
        let overlayContent = document.getElementById("overlay-content")
        let currentEntityId = overlayContent.href
        let oldEntity = JSON.parse(overlayContent.getAttribute("data-entity"))

        let selectedEntityId = target.getElementsByClassName("overlay-entity-link")[0].href

        if(currentEntityId === selectedEntityId){
            return
        }

        let checkmarks = document.querySelectorAll(".checkmark.visible")
        for(let checkmark of checkmarks){
            checkmark.classList.remove("visible")
            checkmark.classList.add("hidden")
        }

        let newCheckmark = target.getElementsByClassName("checkmark")[0]
        newCheckmark.classList.remove("hidden")
        newCheckmark.classList.add("visible")

        if (kgVis === null){
            kgVis = new KgVis({triples: [], entities: []})
            kgVis.draw(document.getElementById("kg-vis"))
            kg = emptyKG()
        }
        let selectedEntity = entityCache.get(selectedEntityId)


        if("mentions" in oldEntity){
            for(let mention of oldEntity.mentions){
                let span = document.getElementById(mention.start_idx+":"+mention.end_idx+":"+mention.url)
                selectedEntity.start_idx = mention.start_idx
                selectedEntity.end_idx = mention.end_idx
                let newSpan = createEntitySpan(selectedEntity)
                span.replaceWith(newSpan)
            }
        }else{
            let span = document.getElementById(oldEntity.start_idx+":"+oldEntity.end_idx+":"+oldEntity.url)
            selectedEntity.start_idx = oldEntity.start_idx
            selectedEntity.end_idx = oldEntity.end_idx
            let newSpan = createEntitySpan(selectedEntity)
            span.replaceWith(newSpan)
        }

        updateKG(oldEntity, selectedEntity)
        kgVis.update(kg)

        document.getElementById("overlay-content").href = selectedEntityId
        updateEntityChangePanel(selectedEntity)
    }
}

function updateKG(oldEntity, newEntity){
    let oldEntities = kg.entities.filter(e => e.url === oldEntity.url)
    // clicked on node in vis
    if ("mentions" in oldEntity){
        if(newEntity === null){
            kg.entities = kg.entities.filter(e => e.url !== oldEntity.url)
        }else{
            for(let entity of oldEntities){
                entity.description = newEntity.description
                entity.e_type = ""
                entity.label = newEntity.label
                entity.score = newEntity.score
                entity.url = newEntity.url

                for(let mention of entity.mentions){
                    mention.description = newEntity.description
                    mention.e_type = ""
                    mention.label = newEntity.label
                    mention.score = newEntity.score
                    mention.url = newEntity.url
                }

                for (let triple of kg.triples){
                    if (triple.subject.url === oldEntity.url){
                        triple.subject = entity
                    }
                    if (triple.object.url === oldEntity.url){
                        triple.object = entity
                    }
                }
            }
        }

    } else{ //clicked on entity mention in editor
        if(newEntity === null){
            for(let entity of kg.entities){
                entity.mentions = entity.mentions.filter(m => !(m.start_idx === oldEntity.start_idx && m.end_idx === oldEntity.end_idx))
            }
        }
        else{
            let newEntities = kg.entities.filter(e => e.url === newEntity.url)
            if(newEntities.length > 0){
                for(let entity of newEntities){
                    let found = false
                    for(let mention of entity.mentions){
                        if(mention.start_idx === oldEntity.start_idx && mention.end_idx === oldEntity.end_idx){
                            mention.description = newEntity.description
                            mention.e_type = ""
                            mention.label = newEntity.label
                            mention.score = newEntity.score
                            mention.url = newEntity.url
                            found = true
                        }
                    }
                }

                for(let entity of oldEntities){
                    entity.mentions = entity.mentions.filter(m => !(m.start_idx === oldEntity.start_idx && m.end_idx === oldEntity.end_idx))
                }
            } else{
                let newUniqueEntity =  {
                        description: newEntity.description,
                        e_type: "",
                        label: newEntity.label,
                        score: newEntity.score,
                        url: newEntity.url,
                        mentions: [newEntity]
                    }
                kg.entities = kg.entities.concat([newUniqueEntity])

                for(let entity of oldEntities){
                    if(entity.mentions.length === 1){
                        kg.entities = kg.entities.filter(e => !(e.url === oldEntity.url))

                        for(let triple of kg.triples){
                            if (triple.subject.url === entity.url){
                                triple.subject = newUniqueEntity
                            }
                            if (triple.object.url === entity.url){
                                triple.object = newUniqueEntity
                            }
                        }
                    }
                }
            }
        }
    }

    kg.entity_mentions = []
    for(let entity of kg.entities){
        kg.entity_mentions =
            kg.entity_mentions.concat(entity.mentions)
    }
    kg.entities = kg.entities.filter(e => e.mentions.length !== 0)
    kg.triples = kg.triples.filter(function (t){
        let sEntities = kg.entities.filter(e => e.url === t.subject.url)
        let oEntities = kg.entities.filter(e => e.url === t.object.url)

        return !(sEntities.length === 0 || oEntities.length === 0);
    })
}

function onKgButtonClicked(e){
    $("#create-kg-button").prop("disabled", true)


    $("#loading-icon").show()
    $("#graph-icon").hide()

    let editor = document.getElementById("text-editor")
    editor.setAttribute("contenteditable", false)

    let editorContent = editor.innerText
    editorContent = editorContent.trim()
    editorContent = editorContent.replaceAll(/[\s\n]+/g, " ")

    let postData = {"content": editorContent}

    requestBackend("POST","/api/v1/kg", null, null, postData, onKgReceive)
    // onKgReceive(JSON.stringify(debugKG()))
}

function onKgReceive(responseText){
    $("#loading-icon").hide()
    $("#graph-icon").show()
    $("#save-button").prop("disabled", false)
    $("#create-kg-button").prop("disabled", false)

    kg = JSON.parse(responseText)
    console.log(kg)


    let entities =  Array.from(kg.entity_mentions)
    entities.sort(function (a, b){return +(a.start_idx - b.start_idx) || -((a.end_idx - a.start_idx) - (b.end_idx - b.start_idx))})
    let textEditor = document.getElementById("text-editor")
    textEditor.setAttribute("contenteditable", true)

    let idx = 0

    if (entities.length > 0){
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
    }

    kgVis = new KgVis(kg)
    kgVis.draw(document.getElementById("kg-vis"))

    kgVis.getNetwork().on("hoverNode", function (e){
        let node = kgVis.getNodeById(e.node)
        if(node === null){
            return
        }
        let url = node.data_entity.url
        let entitySpans = document.querySelectorAll(".entity[href=\""+ url + "\"]")

        for (let entitySpan of entitySpans){
            entitySpan.classList.add("highlight")
        }
    })

    kgVis.getNetwork().on("blurNode", function (e){
        let node = kgVis.getNodeById(e.node)
        if(node === null){
            return
        }
        let url = node.data_entity.url
        let entitySpans = document.querySelectorAll(".entity[href=\""+ url + "\"]")

        for (let entitySpan of entitySpans){
            entitySpan.classList.remove("highlight")
        }
    })

    kgVis.getNetwork().on("click", function (e){
        if(e.nodes.length > 0){
            let node = kgVis.getNodeById(e.nodes[0])
            let entity = node.data_entity

            drawEntityChangePanel(entity)

            kgVis.getNetwork().unselectAll()
        }
    })

    kgVis.getNetwork().on("dragEnd", (opts) => {
          kgVis.getNetwork().unselectAll()
    })

}

function onEntitySearchReceive(responseText){
    let textSpan = document.getElementById("overlay-entity-text-span")

    let data = JSON.parse(responseText)["data"]

    entityCache.clear()
    for (let entity of data){
        entity.url = entity.id
        entity.text = textSpan.innerText;
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
            let entityContainer = entityResultContainer.querySelectorAll(".overlay-entity-container[data-id=\"" + entityId + "\"]")
            if(entityContainer.length > 0){
                let checkmark = entityContainer[0].getElementsByClassName("checkmark")
                checkmark[0].classList.remove("hidden")
                checkmark[0].classList.add("visible")
            }
        })
}

function createEntitySpan(entity){
    let entitySpan = document.createElement("span")
    entitySpan.innerText = entity.text
    entitySpan.classList.add("entity")
    entitySpan.id = `${entity.start_idx}:${entity.end_idx}:${entity.url}`
    entitySpan.setAttribute("href", entity.url)
    entitySpan.setAttribute("data-entity", JSON.stringify(entity))

    entitySpan.appendChild(createEntityDescription(entity))

    entitySpan.addEventListener("click", function (e){
        let entity = e.target.getAttribute("data-entity")
        drawEntityChangePanel(JSON.parse(entity))
    })

    entitySpan.addEventListener("mouseover", function (e){
        if (kgVis !== null){
            let nodes = kgVis.getNodeById(null)
            let node = nodes.filter((n) => n.data_entity.url === e.target.getAttribute("href"))[0]

            if(node !== undefined){
                node.color = { background: getComputedStyle(document.documentElement).getPropertyValue("--highlight-color"),
                highlight: getComputedStyle(document.documentElement).getPropertyValue("--highlight-color"),
                hover: getComputedStyle(document.documentElement).getPropertyValue("--highlight-color")}

                kgVis.updateNode(node)
            }
        }

        let entitySpans = document.querySelectorAll(".entity[href='" + e.target.getAttribute("href")+"']")
        for(let span of entitySpans){
            span.classList.add("highlight")
        }
    })

    entitySpan.addEventListener("mouseout", function (e){
        if (kgVis !== null){
            let nodes = kgVis.getNodeById(null)
            let node = nodes.filter((n) => n.data_entity.url === e.target.getAttribute("href"))[0]
            if(node !== undefined){
                node.color = getComputedStyle(document.documentElement).getPropertyValue("--default-color")

                kgVis.updateNode(node)
            }
        }

        for(let span of $(".entity[href='" + e.target.getAttribute("href")+"']")){
            span.classList.remove("highlight")
        }
    })

    return entitySpan
}

export function createEntityDescription(entity){
    let entityDescription = document.createElement("div")
    entityDescription.classList.add("entity-description")
    entityDescription.setAttribute("contenteditable", false)

    let header = document.createElement("header")
    if (entity.label === null || entity.label === undefined){
        header.innerText = entity.text
    }else{
        header.innerText = entity.label
    }

    entityDescription.appendChild(header)

    entityDescription.appendChild(document.createElement("hr"))

    let description = document.createElement("div")

    if (entity.label === null){
        description.innerText = "literal"
    } else{
        description.innerText = entity.description
    }

    entityDescription.appendChild(description)

    let link = document.createElement("a")
    link.href = entity.url ? entity.url : entity.id
    link.target = "_blank"
    link.innerText = entity.url ? entity.url : entity.id
    entityDescription.appendChild(link)

    entityDescription.addEventListener("click", function (e){
        e.stopPropagation()
    })

    return entityDescription
}

function drawEntityChangePanel(entity){
    let overlay = document.getElementById("overlay-entity")
    overlay.style.display = "flex"

    let overlayContent = document.getElementById("overlay-content")
    overlayContent.href = entity.url
    overlayContent.setAttribute("data-entity", JSON.stringify(entity))

    let entityName

    if ("mentions" in entity){
        entityName = entity.mentions[0].text
    } else{
        entityName = entity.text
    }

    let textSpan = document.getElementById("overlay-entity-text-span")
    textSpan.innerText = entityName

    updateEntityChangePanel(entity)

    let entityResultContainer = document.getElementById("overlay-entity-result-container")
    entityResultContainer.innerHTML = ""

    requestBackend(
        "GET", "https://metareal-kb.web.webis.de/api/v1/kb/entity/search",
        {"q": entityName}, null, null,
        function (responseText) {onEntitySearchReceive(responseText, entityName)})
}

function updateEntityChangePanel(entity){
    let entityName
    if(entity.label !== null){
        entityName = entity.label;
    }  else{
        if ("mentions" in entity){
            entityName = entity.mentions[0].text
        } else{
            entityName = entity.text
        }
    }
    let entityLabel = document.getElementById("overlay-entity-label")
    entityLabel.innerText = entityName

    let entityDescription = document.getElementById("overlay-entity-description")

    if("description" in entity){
        entityDescription.innerText = entity.description
    } else{
        entityDescription.innerText = "literal"
    }
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

function emptyKG(){
    return {
        text: document.getElementById("text-editor").innerText,
        entities: [],
        entity_mentions: [],
        triples: []
    }
}

function download(filename, text) {
  let element = document.createElement('a');
  element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
  element.setAttribute('download', filename);

  element.style.display = 'none';
  document.body.appendChild(element);

  element.click();

  document.body.removeChild(element);
}

function convertToRDF(kg){
    let entityMap = new Map()

    let rdfString = ""
    for(let triple of kg.triples){
        if (triple.object.label === null){
            rdfString += `<${triple.subject.url}> <${triple.predicate.url}> "${triple.object.url}" .\n`
        }else{
            rdfString += `<${triple.subject.url}> <${triple.predicate.url}> <${triple.object.url}> .\n`
            if(!entityMap.has(triple.subject.url)){
                entityMap.set(triple.subject.url, triple.subject)
            }
            if(!entityMap.has(triple.object.url)){
                entityMap.set(triple.object.url, triple.object)
            }
        }
    }

    for(let entity of entityMap.values()){
        rdfString += `<${entity.url}> <${rdfsNS}label> "${entity.label}"@en .\n`
        rdfString += `<${entity.url}> <${schemaNS}description> "${entity.description}"@en .\n`
    }

    rdfString += `<${exampleNS}kg> <${wakaNS}sourceText> "${kg.text}"@en .`

    return rdfString
}