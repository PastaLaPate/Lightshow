from math import cos, sin
from random import uniform
import dearpygui.dearpygui as dpg

#
# TODO: Add another axis & experiment w/ scatter
# 

time = 0
def create_gui():
    dpg.create_context()
    dpg.create_viewport(title='Lightshow GUI', width=600, height=300)

    with dpg.window(label="Lightshow GUI", no_collapse=True, tag="main"):
        dpg.add_text("Lightshow GUI")
        list_box = ["option 1", "option 2", "option 3"]
        dpg.add_listbox(items=list_box, label="Listbox", tag="listbox")
        dpg.add_button(label="Button", tag="Button")
        def add_item():
            list_box.append(f"option {len(list_box) + 1}")
            dpg.configure_item("listbox", items=list_box)
        with dpg.item_handler_registry(tag="item_handler"):
            dpg.add_item_clicked_handler(callback=add_item)
        dpg.bind_item_handler_registry("Button", "item_handler")
        dpg.add_input_text(label="string", default_value="Quick brown fox")
        dpg.add_slider_float(label="float", default_value=0.273, max_value=1)
        with dpg.plot(tag="_plot", width=800, height=400):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="x_axis")
            with dpg.plot_axis(dpg.mvYAxis, label="Amplitude", tag="y_axis"):
                dpg.set_axis_limits("y_axis", -1.1, 1.1)
                dpg.add_line_series([], [], label="Sine Wave", tag="_sin")
                dpg.add_line_series([], [], label="Cos Wave", tag="_cos")
                dpg.add_scatter_series([], [], label="Scatter", tag="_scatter")
        data = [[], [], []]
        def update_plot():
            global time
            time += dpg.get_delta_time()
            dpg.set_axis_limits("x_axis", max(0, time - 10), time)
            data[0].append([time, sin(time)])
            dpg.set_value("_sin", [*zip(*data[0])])
            data[1].append([time, cos(time)])
            dpg.set_value("_cos", [*zip(*data[1])])
            if uniform(0, 1) < 0.01:    
                data[2].append([time, uniform(-1, 1)])
                dpg.set_value("_scatter", [*zip(*data[2])])
        with dpg.item_handler_registry(tag="plot_handler"):
            dpg.add_item_visible_handler(callback=update_plot)
        dpg.bind_item_handler_registry("_plot", "plot_handler")
    dpg.set_primary_window("main", True)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
    
if __name__ == "__main__":
    create_gui()