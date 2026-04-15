from PIL import Image
import numpy as np

src = r"c:\Users\DIEGO\Documents\PROJETO FLOTADOR\logo nova.png"
dst = r"c:\Users\DIEGO\Documents\PROJETO FLOTADOR\logo nova_transparent.png"

img = Image.open(src).convert("RGBA")
data = np.array(img)

r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
# Marca pixels brancos/quase-brancos como transparentes
white = (r > 230) & (g > 230) & (b > 230)
data[white, 3] = 0

result = Image.fromarray(data, mode="RGBA")
result.save(dst)
print(f"Salvo em: {dst}")
