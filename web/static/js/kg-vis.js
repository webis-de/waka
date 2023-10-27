import {createEntityDescription} from "./main.js"

export class KgVis{
    static #defaultOptions = {
        interaction: {
            hover: true,
            hoverConnectedEdges: false,
            selectable: false,
            selectConnectedEdges: false,
            navigationButtons: true,
            tooltipDelay: 0
        },
        layout: {improvedLayout: false},
        physics: {enabled: true, solver: "forceAtlas2Based",
            repulsion: {
                damping: 1,
                nodeDistance: 300
            }, forceAtlas2Based: {
                avoidOverlap: 0
            }}
    };

    static #defaultEdgeOptions = {
        color: "#000",
        font: {
            face: "Curier",
            color: "#000",
            bold: true
        },
        arrows: {
            to:  true
        }
    }

    static #defaultNodeOptions = {
        chosen: {
            node: function (values, id, selected, hovering) {
                if (!hovering) {
                    values.color = getComputedStyle(document.documentElement).getPropertyValue("--default-color")
                } else {
                    values.color = getComputedStyle(document.documentElement).getPropertyValue("--highlight-color")
                }
            },
            label: function (values, id, selected, hovering) {
                if (!hovering) {
                    values.mod = false
                }
            }
        },
        color: {
            border: "white",
            background: getComputedStyle(document.documentElement).getPropertyValue("--default-color"),
            hover: {
                background: getComputedStyle(document.documentElement).getPropertyValue("--highlight-color"),
            }
        },
        font: {
            face: "Curier",
            color: "#fff",
            bold: true
        }
    }

    #nodes = new vis.DataSet();
    #edges = new vis.DataSet();

    #network

    constructor(kg) {
        this.#network = null

        let nodesMap = new Map()
        let edges = []

        for (let triple of kg.triples){
            if(!nodesMap.has(triple.subject.url)){
                nodesMap.set(triple.subject.url,
                    KgVis.createNodeFromEntity(triple.subject))
            }

            if(!nodesMap.has(triple.object.url)){
                nodesMap.set(triple.object.url,
                    KgVis.createNodeFromEntity(triple.object))
            }

            let edge = KgVis.createEdgeFromTriple(triple)
            edges.push(edge)
        }

        this.#nodes.add(Array.from(nodesMap.values()))
        this.#edges.add(edges)
    }

    static createNodeFromEntity(entity) {
        return {
            id: entity.url ? entity.url : entity.id,
            label: entity.label ? entity.label : entity.text,
            title: createEntityDescription(entity),
            ...KgVis.#defaultNodeOptions
        }
    }

    static createEdgeFromTriple(triple) {
        return {
            from: triple.subject.url,
            to: triple.object.url,
            label: triple.predicate.text,
            title: createEntityDescription(triple.predicate),
            ...KgVis.#defaultEdgeOptions
        }
    }

    draw(container){
        let data = {
            nodes: this.#nodes,
            edges: this.#edges
        };

        this.#network = new vis.Network(container, data, KgVis.#defaultOptions)
        let _self = this
        this.#network.on("stabilizationIterationsDone", function (){
            _self.#network.setOptions({physics: {enabled: false}})
        })

        // TODO: To main
        this.#network.on("hoverNode", function (e){
            let entitySpans = document.querySelectorAll("[href=\""+ e.node + "\"]")

            for (let entitySpan of entitySpans){
                entitySpan.classList.add("highlight")
            }
        })

        // TODO: To main
        this.#network.on("blurNode", function (e){
            let entitySpans = document.querySelectorAll("[href=\""+ e.node + "\"]")

            for (let entitySpan of entitySpans){
                entitySpan.classList.remove("highlight")
            }
        })
    }

    getNodeById(id){
        return this.#nodes.get(id)
    }

    getNetwork(){
        return this.#network
    }

    addNode(node){
        this.#nodes.update(node)
    }
}