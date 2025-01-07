import asyncio
import json
from fastapi import Request
from nicegui import app, ui, binding

from PIL import Image, ImageDraw, ImageFont

app.add_media_files("/assets", "assets")

binding.MAX_PROPAGATION_TIME = 0.05 # from 0.01 to 0.05

LINE_NEIGHRBOR_LIST = [] 

import datetime
import time 

def format_time():
    t = datetime.datetime.now()
    s = t.isoformat(timespec='milliseconds')
    return s

# PORT 1: Up port
# PORT 2: Right port
# PORT 3: Down port
# PORT 4: Left port

def gen_grid_image(up, right, down, left):
    # draw the face of one grid, the grid is of a cross shape, with 4 ports, up, right, down, left
    # up, right, down, left are boolean, if True, draw a line, to center. If not, draw nothing
    # create a new image with white background
    img = Image.new('RGB', (50, 50), color = (255, 255, 255))
    if up:
        d = ImageDraw.Draw(img)
        d.line([25, 0, 25, 25], fill="black", width=10)
    if right:
        d = ImageDraw.Draw(img)
        d.line([25, 25, 50, 25], fill="black", width=10)
    if down:
        d = ImageDraw.Draw(img)
        d.line([25, 25, 25, 50], fill="black", width=10)
    if left:
        d = ImageDraw.Draw(img)
        d.line([0, 25, 25, 25], fill="black", width=10)

    return img

# save all variants of the grid image to /assets/grid_URDL.png
for up in [True, False]:
    for right in [True, False]:
        for down in [True, False]:
            for left in [True, False]:
                filename = f"assets/grid_{up}_{right}_{down}_{left}.png"
                img = gen_grid_image(up, right, down, left)
                img.save(filename)

PAYLOAD_TO_PORTS = {
    0: [True, True, True, True], # center
    871: [True, False, False, True], # right
}

PAYLOAD_TO_IMAGE = {
    payload: f"assets/grid_{up}_{right}_{down}_{left}.png"
    for payload, (up, right, down, left) in PAYLOAD_TO_PORTS.items()
}


def reset_grid():
    global grid
    grid = [[{"ID": None, "Payload": None, "PortToSky": None, "Populated": False, "UpOPEN": False, "RightOPEN": False, "DownOPEN": False, "LeftOPEN": False} for _ in range(15)] for _ in range(15)]
    grid[7][7] = {"ID": 0, "Payload": 0, "PortToSky": 1, "Populated": True, "LeftOPEN": True, "RightOPEN": True, "UpOPEN": True, "DownOPEN": True}
    LINE_NEIGHRBOR_LIST.clear()

def ensure_1_2_3_4(value):
    # ensure value is 1, 2, 3 or 4, 5 -> 1, 6 -> 2, 7 -> 3, 8 -> 4, etc.
    return (value - 1) % 4 + 1  


def render_all_grid_image(grid_dict, filename):

    # create a new image with white background
    img = Image.new('RGB', (15*50, 15*50), color = (255, 255, 255))

    # create a draw object
    d = ImageDraw.Draw(img)

    # load a font
    fnt = ImageFont.load_default()

    for row in range(15):
        for col in range(15):
            cell = grid_dict[row][col]
            if cell["Populated"]:
                """# draw a rectangle
                d.rectangle([col*50, row*50, (col+1)*50-1, (row+1)*50-1], outline="black", width=2)
                # draw the ID
                d.text((col*50+5, row*50+5), "ID:"+str(cell["ID"]), font=fnt, fill=(0,0,0))
                # draw the payload
                d.text((col*50+5, row*50+20), "P:"+str(cell["Payload"]), font=fnt, fill=(0,0,0))
                # draw the port to sky
                d.text((col*50+5, row*50+35), "PTS:"+str(cell["PortToSky"]), font=fnt, fill=(0,0,0))"""
                # put the image of the cell
                img_cell = Image.open(PAYLOAD_TO_IMAGE.get(cell["Payload"], "assets/grid_False_False_False_False.png"))

                # rotate the image according to the port to sky
                img_cell = img_cell.rotate((cell["PortToSky"]-1)*90)
                img.paste(img_cell, (col*50, row*50))

                # put the ID at the top left corner
                d.text((col*50+5, row*50+5), str(cell["ID"]), font=fnt, fill=(0,0,0))

                # put dots for open ports
                if cell["UpOPEN"]:
                    d.ellipse([col*50+20, row*50, col*50+30, row*50+10], fill="red")
                if cell["RightOPEN"]:
                    d.ellipse([col*50+40, row*50+20, col*50+50, row*50+30], fill="red")
                if cell["DownOPEN"]:
                    d.ellipse([col*50+20, row*50+40, col*50+30, row*50+50], fill="red")
                if cell["LeftOPEN"]:
                    d.ellipse([col*50, row*50+20, col*50+10, row*50+30], fill="red")
            else:
                # draw a rectangle
                d.rectangle([col*50, row*50, (col+1)*50-1, (row+1)*50-1], outline="black", width=1)

    img.save(filename)


@app.post("/console/{text_ip}/{text_channel}")
async def console(text_ip: str, text_channel: str, request: Request):
    text_content = (await request.body()).decode()
    if text_channel == "showip":
        print(format_time(), "IP address:", text_ip, ": ", text_content)
        # write ip in app.strorage.general["ip_boottime"] dictionary, key is ip address, value is boot time (current unix time)
        if not "ip_boottime" in app.storage.general:
            app.storage.general["ip_boottime"] = {}
        app.storage.general["ip_boottime"][text_ip] = time.time()

        # write also the ip_boottext in a similar way
        if not "ip_boottext" in app.storage.general:
            app.storage.general["ip_boottext"] = {}
        app.storage.general["ip_boottext"][text_ip] = text_content

    elif text_channel == "debug":
        # print(format_time(), "Message from", text_ip, ":", text_content)
        if not text_ip in app.storage.general:
            app.storage.general[text_ip] = []
        app.storage.general[text_ip].append(text_content)
        # keep last 10 messages
        app.storage.general[text_ip] = app.storage.general[text_ip][-10:]

    elif text_channel == "conninfo":
        try:
            reset_grid()
            conn_info = json.loads(text_content)

            """{
    "EdgeConnections": {
        "ConnectionCount": 1,
        "Connections": [
            {
                "Connection": 1,
                "srcPort": 2,
                "srcBoardID": 0,
                "connPort": 4,
                "connBoardLevel": 1,
                "connBoardID": 44,
                "connPayloadID": 871
            }
        ]
    }
}"""


            for conn in conn_info["EdgeConnections"]["Connections"]:
                print(format_time(), "=== Connection from", text_ip, ":", conn)
                """ {'Connection': 1, 'srcPort': 2, 'srcBoardID': 0, 'connPort': 4, 'connBoardLevel': 1, 'connBoardID': 44, 'connPayloadID': 871}"""
                # find the source board in the grid
                for row in range(15):
                    for col in range(15):
                        if grid[row][col]["ID"] == conn["srcBoardID"]:
                            # here, the source board is found
                            # now, depending on the source port, we can find where (up, right, down, left) the connected board is
                            row_conn = row
                            col_conn = col

                            connected_port_position = conn["srcPort"] - (grid[row][col]["PortToSky"] - 1)

                            connected_port_position = ensure_1_2_3_4(connected_port_position)
                            
                            if connected_port_position == 1:
                                #print(format_time(), "=== Connected to up")
                                row_conn -= 1 # up
                            elif connected_port_position == 2:
                                #print(format_time(), "=== Connected to right")
                                col_conn += 1 # right
                            elif connected_port_position == 3:
                                #print(format_time(), "=== Connected to down")
                                row_conn += 1 # down
                            elif connected_port_position == 4:
                                #print(format_time(), "=== Connected to left")
                                col_conn -= 1 # left

                            conn_board_port_to_sky = 1 + (conn["connPort"] - connected_port_position + 2)
                            conn_board_port_to_sky = ensure_1_2_3_4(conn_board_port_to_sky)

                            #print(format_time(), "=== Connected board port to sky:", conn_board_port_to_sky)

                            open_status = PAYLOAD_TO_PORTS.get(conn["connPayloadID"], [False, False, False, False])

                            grid[row_conn][col_conn] = {"ID": conn["connBoardID"], "Payload": conn["connPayloadID"], "PortToSky": conn_board_port_to_sky, "Populated": True, 
                                                        "UpOPEN": open_status[ensure_1_2_3_4(1 + (conn_board_port_to_sky - 1)) - 1],
                                                        "RightOPEN": open_status[ensure_1_2_3_4(2 + (conn_board_port_to_sky - 1)) - 1],
                                                        "DownOPEN": open_status[ensure_1_2_3_4(3 + (conn_board_port_to_sky - 1)) - 1],
                                                        "LeftOPEN": open_status[ensure_1_2_3_4(4 + (conn_board_port_to_sky - 1)) - 1]}
                            
                            # check the neighbors of the connected board. if the corresponding port is open (say, my Up and his Down), then add to LINE_NEIGHRBOR_LIST

                            # check the up neighbor, aka row_conn-1, col_conn
                            if grid[row_conn][col_conn]["UpOPEN"] and grid[row_conn-1][col_conn]["DownOPEN"]:
                                LINE_NEIGHRBOR_LIST.append([grid[row_conn][col_conn]["ID"], grid[row_conn-1][col_conn]["ID"]])
                            # check the right neighbor, aka row_conn, col_conn+1
                            if grid[row_conn][col_conn]["RightOPEN"] and grid[row_conn][col_conn+1]["LeftOPEN"]:
                                LINE_NEIGHRBOR_LIST.append([grid[row_conn][col_conn]["ID"], grid[row_conn][col_conn+1]["ID"]])
                            # check the down neighbor, aka row_conn+1, col_conn
                            if grid[row_conn][col_conn]["DownOPEN"] and grid[row_conn+1][col_conn]["UpOPEN"]:
                                LINE_NEIGHRBOR_LIST.append([grid[row_conn][col_conn]["ID"], grid[row_conn+1][col_conn]["ID"]])
                            # check the left neighbor, aka row_conn, col_conn-1
                            if grid[row_conn][col_conn]["LeftOPEN"] and grid[row_conn][col_conn-1]["RightOPEN"]:
                                LINE_NEIGHRBOR_LIST.append([grid[row_conn][col_conn]["ID"], grid[row_conn][col_conn-1]["ID"]])

                            # print("grid", grid)
                            break
                            
                            # now, the connected board is at row_conn, col_conn

            formatted_content = json.dumps(conn_info, indent=4)
            #print(format_time(), "=== Connection info from", text_ip, ":", formatted_content)
            render_all_grid_image(grid, "assets/grid.png")
        except json.JSONDecodeError:
            #print(format_time(), "=== Connection info from", text_ip, ":", text_content, "(Invalid JSON)")
            pass

    return None

@ui.page("/viewconsole/{text_ip}")
def viewconsole(text_ip: str):
    ui.label(f"Viewing console for {text_ip}")
    mycode = ui.code().classes("w-full h-96")
    mycode.bind_content_from(app.storage.general, text_ip, backward=lambda x: "\n".join(x))

@ui.page("/")
def index():
    # assert ip_boottime dictionary in app.storage.general, also ip_boottext
    if not "ip_boottime" in app.storage.general:
        app.storage.general["ip_boottime"] = {}
    if not "ip_boottext" in app.storage.general:
        app.storage.general["ip_boottext"] = {}

    # show the ip address in ip_boottime dictionary, sorted by most recently booted first
    if "ip_boottime" in app.storage.general:
        ip_boottime = app.storage.general["ip_boottime"]
        ip_boottime = dict(sorted(ip_boottime.items(), key=lambda item: item[1], reverse=True))
        for ip, boottime in ip_boottime.items():
            ui.label(f"{ip} - {datetime.datetime.fromtimestamp(boottime).isoformat()} - {app.storage.general['ip_boottext'].get(ip, '')}")
            ui.button(f"OPEN {ip}", on_click=lambda ip=ip: ui.navigate.to(f"/viewconsole/{ip}"))

@ui.page("/grid")
def grid_page():
    with ui.column().classes("aspect-square"):
        with ui.column().classes("grid grid-cols-[repeat(15,_minmax(0,_1fr))] gap-1"):
            for row in grid:
                if True: #with ui.row():
                    for cell in row:
                        ui.image("/assets/R.png").classes("w-12 h-12")
                        """if cell["Populated"]:
                            # ui.label("Yes")
                            ui.label(f"{cell['ID']}, {cell['Payload']}, {cell['PortToSky']}")
                        else:
                            ui.label("Empty")  """ 

@ui.page("/gridimage")
async def grid_image_page():
    # render_all_grid_image(grid, "assets/grid.png")
    img = ui.image("assets/grid.png").classes("w-96 h-96")
    img.force_reload()
    ui.label(str(LINE_NEIGHRBOR_LIST))

    await ui.context.client.connected()

    await asyncio.sleep(5)
    ui.navigate.reload()

ui.run()