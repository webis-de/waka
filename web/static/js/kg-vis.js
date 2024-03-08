import {createEntityDescription} from "./main.js"

export class KgVis{
    static #defaultOptions = {
        interaction: {
            hover: true,
            hoverConnectedEdges: false,
            selectable: true,
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

        for (let entity of kg.entities){
             if(!nodesMap.has(entity.url)){
                nodesMap.set(entity.url,
                    KgVis.createNodeFromEntity(entity))
             }
        }

        for (let triple of kg.triples){
            let edge = KgVis.createEdgeFromTriple(triple)
            edges.push(edge)
        }

        this.#nodes.add(Array.from(nodesMap.values()))
        this.#edges.add(edges)
    }

    static createNodeFromEntity(entity) {
        let uniqueEntity = entity
        if (!"mentions" in entity){
            uniqueEntity = {
                description: entity.description,
                e_type: "entity",
                label: entity.label,
                mentions: [entity],
                score: entity.score,
                url: entity.url
            }
        }

        return {
            id: entity.url ? entity.url : entity.id,
            label: entity.e_type === "literal" ? entity.mentions[0].text : entity.label,
            title: createEntityDescription(entity),
            data_entity: uniqueEntity,
            ...KgVis.#defaultNodeOptions
        }
    }

    static createEdgeFromTriple(triple) {
        return {
            id: triple.id_,
            from: triple.subject.url,
            to: triple.object.url,
            label: triple.predicate.text,
            title: createEntityDescription(triple.predicate),
            data_triple: triple,
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
    }

    getNodeById(id){
        return this.#nodes.get(id)
    }

    getNetwork(){
        return this.#network
    }

    updateNode(node){
        this.#nodes.update(node)
    }

    update(kg){
        for(let entity of kg.entities){
            this.updateNode(KgVis.createNodeFromEntity(entity))
        }

        let _this = this
        this.#nodes.forEach(function (node) {
            if(kg.entities.filter(e => e.url === node.id).length === 0){
                _this.#nodes.remove(node.id)
            }
        })

        for(let triple of kg.triples){
            this.#edges.update(KgVis.createEdgeFromTriple(triple))
        }
    }

    removeNode(node){
        this.#nodes.remove(node.id)
    }
}