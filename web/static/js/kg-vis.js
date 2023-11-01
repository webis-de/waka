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
             }else{
                 let node = nodesMap.get(entity.url)
                 node.of_triple[entity.text] = entity.of_triple
             }
        }

        for (let triple of kg.triples){
            // if(!nodesMap.has(triple.subject.url)){
            //     nodesMap.set(triple.subject.url,
            //         KgVis.createNodeFromEntity(triple.subject))
            // }
            //
            // if(!nodesMap.has(triple.object.url)){
            //     nodesMap.set(triple.object.url,
            //         KgVis.createNodeFromEntity(triple.object))
            // }

            let edge = KgVis.createEdgeFromTriple(triple)
            edges.push(edge)
        }

        this.#nodes.add(Array.from(nodesMap.values()))
        this.#edges.add(edges)
    }

    static createNodeFromEntity(entity) {
        let of_triple
        if(Array.isArray(entity.of_triple)){
            of_triple = {}
            of_triple[entity.text] = entity.of_triple
        } else{
            of_triple = entity.of_triple
        }


        return {
            id: entity.url ? entity.url : entity.id,
            label: entity.label ? entity.label : entity.text,
            title: createEntityDescription(entity),
            of_triple: of_triple,
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

    replaceNode(text, oldNode, newNode){
        if(oldNode !== null){
            if(Object.keys(oldNode.of_triple).length === 1){
                this.#nodes.remove(oldNode.id)
            }/*else{
                newNode.of_triple = {}
                newNode.of_triple[text] = oldNode.of_triple[text]
            }*/

            let edgeUpdates =
                this.#edges.map(function (e){
                    if(oldNode.of_triple[text].includes(e.id)){
                        if(e.from === oldNode.id){
                            e.from = newNode.id
                        }

                        if(e.to === oldNode.id){
                            e.to = newNode.id
                        }
                    }

                    return e
                })

            this.#edges.update(edgeUpdates)
        }
        this.#nodes.update(newNode)
    }

    removeNode(node){
        this.#nodes.remove(node.id)
    }
}