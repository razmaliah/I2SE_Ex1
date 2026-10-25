import numpy as np

def sample_line(volume, a, b):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)

    direction = b-a      # TODO
    dist = np.linalg.norm(direction)           # TODO
    # TODO: what happens if a == b? (dist == 0)
    if dist==0:
        dp = np.zeros(3, dtype=float)
    else:
        dp = direction / dist               # TODO
    n = int(dist) + 1       # TODO: how many samples?
    result = np.zeros(n, dtype=volume.dtype)
    p = a.copy()
    sx, sy, sz = volume.shape
    for i in range(n):
        idx = np.round(p).astype(int)  
        if idx[0]<0 or idx[1]<0 or idx[2]<0 or idx[0]>=sx or idx[1]>=sy or idx[2]>=sz:
            result[i] = 0
        else:
            result[i] = volume[idx[0], idx[1], idx[2]]    
        p = p + dp
    return result

xyz = np.arange(27).reshape(3,3,3)
a = [0,0,0]
b = [4,0,0]
sample_line(xyz, a, b)

print(sample_line(xyz, (0,0,0), (2,1,1)))   # [ 0  9 18]
print(sample_line(xyz, (0,0,0), (4,0,0)))   # [ 0  9 18  0  0]
print(sample_line(xyz, (0,0,0), (0,0,2)))   # [0 1 2]
print(sample_line(xyz, (1,1,1), (1,1,1)))   # [13]  ← a == b
