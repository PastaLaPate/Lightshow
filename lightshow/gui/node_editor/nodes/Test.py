from qtpynodeeditor import NodeData, NodeDataModel, NodeDataType, PortType


class MyNodeData(NodeData):
    data_type = NodeDataType(id="MyNodeData", name="My Node Data")


class SimpleNodeData(NodeData):
    data_type = NodeDataType(id="SimpleData", name="Simple Data")


class NaiveDataModel(NodeDataModel):
    name = "NaiveDataModel"
    caption = "Caption"
    caption_visible = True
    num_ports = {
        PortType.input: 2,
        PortType.output: 2,
    }
    data_type = {
        PortType.input: {0: MyNodeData.data_type, 1: SimpleNodeData.data_type},
        PortType.output: {0: MyNodeData.data_type, 1: SimpleNodeData.data_type},
    }

    def out_data(self, port_index):
        if port_index == 0:
            return MyNodeData()
        elif port_index == 1:
            return SimpleNodeData()

    def set_in_data(self, node_data, port): ...

    def embedded_widget(self): ...
