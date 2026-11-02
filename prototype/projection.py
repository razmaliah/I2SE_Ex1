import numpy as np
EPS = 0.001

def sample_line(volume, a, b):
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)

    direction = b-a      
    dist = np.linalg.norm(direction)          

    if dist == 0:
        dp = np.zeros(3, dtype=float)
    else:
        dp = direction / dist              
    n = int(dist) + 1       
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

def project_triangle(volume, a, b, c):
    a, b, c = (np.array(p, dtype=float) for p in (a, b, c))
    v_ab = b-a          
    v_ac = c-a  
    Dab = np.linalg.norm(v_ab)
    Dac = np.linalg.norm(v_ac)
    if abs(Dab-Dac)>EPS:
        raise ValueError(f"Triangle is not isosceles: |ab|={Dab:.4f}, |ac|={Dac:.4f}")
    Dbc = np.linalg.norm(c-b)           
    E = np.zeros((int(Dab) + 1, int(Dbc) + 1), dtype=volume.dtype)
    if Dab<EPS :
        vn_ab = np.zeros(3, dtype=float)
        vn_ac = np.zeros(3, dtype=float)
    else:
        vn_ab = v_ab/Dab
        vn_ac = v_ac/Dac          
    for y in range(int(Dab) + 1):
        a1 = a + y*vn_ab                       
        a2 = a + y*vn_ac                         
        row = sample_line(volume, a1, a2)
        start = (E.shape[1] - len(row)) // 2             
        E[y, start:start + len(row)] = row

    return E

if __name__ == "__main__":
    vol = np.ones((10, 10, 1), dtype=int)
    print(project_triangle(vol, (1,4,0), (5,1,0), (5,7,0)))