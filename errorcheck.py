import os, hover_click_component

print(">>> init file =", hover_click_component.__file__)
print(">>> listdir(frontend) =", os.listdir(
    os.path.join(os.path.dirname(hover_click_component.__file__), "frontend")
))
