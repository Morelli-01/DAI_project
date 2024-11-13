import tkinter as tk
import math

# Configurazione del numero di processi
n_processi = 10
token_holder = 0  # Il processo che inizialmente detiene il token
radius = 150  # Raggio del cerchio per la disposizione dei processi
circle_size = 30  # Dimensione dei cerchi per ogni processo
arrow_offset = 20  # Distanza della punta della freccia dal bordo del cerchio


# Funzione per disegnare i processi in un cerchio e collegarli con frecce
def draw_ring():
    canvas.delete("all")  # Pulisci il canvas
    angle_step = 2 * math.pi / n_processi  # Angolo tra i processi

    positions = []
    for i in range(n_processi):
        # Calcola la posizione di ogni processo in un cerchio
        angle = i * angle_step
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        positions.append((x, y))

        # Disegna il processo come un cerchio con ID al centro
        color = "red" if i == token_holder else "lightblue"
        canvas.create_oval(x - circle_size, y - circle_size, x + circle_size, y + circle_size, fill=color)
        canvas.create_text(x, y, text=str(i), font=("Arial", 12, "bold"))

    # Disegna le frecce per collegare i processi in modo circolare
    for i in range(n_processi):
        start_x, start_y = positions[i]
        end_x, end_y = positions[(i + 1) % n_processi]

        # Calcola l'angolo della freccia e applica un offset per la punta
        angle = math.atan2(end_y - start_y, end_x - start_x)
        start_x_offset = start_x + arrow_offset * math.cos(angle)
        start_y_offset = start_y + arrow_offset * math.sin(angle)
        end_x_offset = end_x - arrow_offset * math.cos(angle)
        end_y_offset = end_y - arrow_offset * math.sin(angle)

        draw_arrow(start_x_offset, start_y_offset, end_x_offset, end_y_offset)


# Funzione per disegnare una freccia tra due punti con un offset
def draw_arrow(x1, y1, x2, y2):
    canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, width=2)


# Funzione per aggiornare il nodo che detiene il token
def update_token():
    global token_holder
    token_holder = (token_holder + 1) % n_processi  # Passa al prossimo nodo
    draw_ring()  # Ridisegna il ring con il token aggiornato


def start_GUI():
    # Configura la finestra principale di Tkinter
    root = tk.Tk()
    root.title("Token Ring Visualization")

    # Configura il canvas per disegnare i processi
    canvas_size = 400
    global canvas
    canvas = tk.Canvas(root, width=canvas_size, height=canvas_size, bg="white")
    canvas.pack()

    # Centro del cerchio
    global center_x
    global center_y
    center_x = canvas_size / 2
    center_y = canvas_size / 2

    # Pulsante per aggiornare il token
    # button = tk.Button(root, text="Passa Token", command=update_token)
    # button.pack()

    # Disegna il ring iniziale
    draw_ring()

    # Avvia la GUI di Tkinter
    root.mainloop()
