import math
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["SimSun"]
plt.rcParams['axes.unicode_minus'] = False
import numpy as np
M1 = np.array([20000, 0, 2000])
f1 = np.array([17800, 0, 1800])
v_f1 = 120
v_M1 = 300
v_smoke = -3
g = 9.80655
fake_target = np.array([0,0,0])
true_target = np.array([0, 200, 5])  #此为质心，高为10，半径为7
true_target_R = 7
true_target_H = 10
smoke_R = 10
t_list = np.arange(0, 65, 0.004)
true_target_corner_1 = true_target - np.array([0, true_target_R, true_target_H / 2])
true_target_corner_2 = true_target - np.array([0, true_target_R, -true_target_H / 2])
true_target_corner_3 = true_target - np.array([0, -true_target_R, true_target_H / 2])
true_target_corner_4 = true_target - np.array([0, -true_target_R, -true_target_H / 2])
smoke_duration = 20  # 烟雾存续时间
true_target_corners = [true_target_corner_1, true_target_corner_2, true_target_corner_3, true_target_corner_4]


missile_starts = [
    np.array([20000, 0, 2000]),
    np.array([19000, 600, 2100]),
    np.array([18000, -600, 1900])
]

drone_pos = {
    0: np.array([17800,0,1800]),
    1: np.array([12000,1400,1400]),
    2: np.array([6000,-3000,700]),
    3: np.array([11000,2000,1800]),
    4: np.array([13000,-2000,1300])
}


def get_missile_traj(start, target, v, t_list):
    """
    start: np.array([x0, y0, z0]) 导弹初始点
    target: np.array([x1, y1, z1]) 目标点 //为原点的假目标
    v: float 导弹速度（m/s）
    t_list: np.array 时间序列
    返回: (3, T) 导弹轨迹
    """
    direction = (target - start) / np.linalg.norm(target - start)
    traj = start[:, np.newaxis] + v * t_list * direction[:, np.newaxis]
    return traj

def get_smoke_center(position, direction_angle, speed, throw_time, burst_delay, t_list):
    """
    position: np.array([x, y, z]) 无人机初始坐标
    direction_angle: float, 水平飞行方向（0~2pi，弧度）
    speed: float, 无人机飞行速度
    throw_time: float, 投弹时间
    burst_delay: float, 投弹后干扰弹再爆炸的时间
    t_list: np.array, 时间序列
    返回: (3, len(t_list)) 烟雾球心轨迹，未爆炸/超时高度为1e6
    """
    global g
    global v_smoke
    global smoke_duration
    global smoke_R

    direction = np.array([np.cos(direction_angle), np.sin(direction_angle), 0.0])
    t_burst = throw_time + burst_delay
    smoke_center = np.ones((3, len(t_list))) * 1e6  # 默认高度为1e6
    valid_idx = (t_list >= t_burst) & (t_list <= t_burst + smoke_duration)

    # 把抛出后的水平运动也算进无人机位移里
    smoke_start = position + (direction * speed * t_burst) - 0.5 * np.array([0, 0, g]) * burst_delay ** 2
    t_valid = t_list[valid_idx] - t_burst
    smoke_center[:, valid_idx] = smoke_start.reshape(3, 1)
    smoke_center[2, valid_idx] += v_smoke * t_valid  # 仅竖直速度，无重力

    return smoke_center


def get_smoke_center_multi(position, direction_angle, speed, throw_times, burst_delays, t_list):
    """
    position: np.array([x, y, z]) 无人机初始坐标
    direction_angle: float, 水平飞行方向（0~2pi，弧度）
    speed: float, 无人机飞行速度
    throw_times: 长度为3的递增数组，三次投弹时间，且相邻间隔>=1
    burst_delays: 长度为3的数组，对应每次投弹后的爆炸延迟
    t_list: np.array, 时间序列
    返回: (3, len(t_list), 3) 三个干扰弹的球心轨迹
    """
    global g
    global v_smoke
    global smoke_duration

    throw_times = np.array(throw_times)
    burst_delays = np.array(burst_delays)
    assert len(throw_times) == 3 and len(burst_delays) == 3
    assert np.all(np.diff(throw_times) >= 1), "投弹时间需递增且间隔>=1"

    direction = np.array([np.cos(direction_angle), np.sin(direction_angle), 0.0])
    smoke_centers = np.ones((3, len(t_list), 3)) * 1e6  # (x,y,z), 时间, 弹序号

    for i in range(3):
        t_burst = throw_times[i] + burst_delays[i]
        valid_idx = (t_list >= t_burst) & (t_list <= t_burst + smoke_duration)
        smoke_start = position + (direction * speed * t_burst) - 0.5 * np.array([0, 0, g]) * burst_delays[i]**2
        t_valid = t_list[valid_idx] - t_burst
        smoke_centers[:, valid_idx, i] = smoke_start.reshape(3, 1)
        smoke_centers[2, valid_idx, i] += v_smoke * t_valid

    return smoke_centers


def get_cover_intervals(covered, t_list):
    """
    covered: bool数组，表示每一时刻是否被遮挡
    t_list: 时间序列
    返回：intervals列表，每个元素为(起始时刻, 结束时刻)
    """
    covered = np.asarray(covered)
    # 找到遮挡区间的起止点
    changes = np.diff(covered.astype(int))
    starts = np.where(changes == 1)[0] + 1
    ends = np.where(changes == -1)[0] + 1

    # 如果开头就是遮挡
    if covered[0]:
        starts = np.insert(starts, 0, 0)
    # 如果结尾是遮挡
    if covered[-1]:
        ends = np.append(ends, len(covered))

    intervals = [(t_list[s], t_list[e-1]) for s, e in zip(starts, ends)]
    return intervals








def get_missile_cover_time(smoke_center, missile_traj, true_target, smoke_radius, t_list, debug=False):

    """
    smoke_center: (3, T) 烟雾球心轨迹
    missile_traj: (3, T) 导弹轨迹
    true_target: np.array([x, y, z]) 目标点
    smoke_radius: float, 烟雾半径
    t_list: np.array, 时间序列
    返回: 遮挡总时间（float），并打印所有遮挡区间的起止时刻
    """
    P = smoke_center.T  # shape (T, 3)
    A = missile_traj.T
    B = np.broadcast_to(true_target, A.shape)
    AB = B - A
    AP = P - A
    cross = np.cross(AP, AB)
    dist = np.linalg.norm(cross, axis=1) / np.linalg.norm(AB, axis=1)
    t_proj = np.sum(AP * AB, axis=1) / np.sum(AB * AB, axis=1)
    on_segment = (t_proj >= 0) & (t_proj <= 1)
    covered = (dist < smoke_radius) & on_segment

    # 统计遮挡区间
    total_cover_time = np.sum(covered) * (t_list[1] - t_list[0])
    # 打印所有遮挡区间
    if debug:
        intervals = get_cover_intervals(covered, t_list)
        for start, end in intervals:
            print(f'遮挡区间: {start:.2f}s ~ {end:.2f}s')
        
        print(f'总遮挡时间: {total_cover_time:.2f}s')

    return total_cover_time



def get_missile_cover_time_corners(smoke_center, missile_traj, true_target_corners, smoke_radius, t_list, debug=False):
    """
    smoke_center: (3, T) 烟雾球心轨迹
    missile_traj: (3, T) 导弹轨迹
    true_target_corners: list of 4 np.array([x, y, z]) 目标四个角点
    smoke_radius: float, 烟雾半径
    t_list: np.array, 时间序列
    返回: 遮挡总时间（float），并打印所有遮挡区间的起止时刻
    """
    covered_all = np.ones(len(t_list), dtype=bool)
    for corner in true_target_corners:
        P = smoke_center.T  # shape (T, 3)
        A = missile_traj.T
        B = np.broadcast_to(corner, A.shape)
        AB = B - A
        AP = P - A
        cross = np.cross(AP, AB)
        t_proj = np.sum(AP * AB, axis=1) / np.sum(AB * AB, axis=1)
        on_segment = (t_proj >= 0) & (t_proj <= 1)
        dist = np.linalg.norm(cross, axis=1) / np.linalg.norm(AB, axis=1)
        covered = (dist < smoke_radius) & on_segment
        covered = dist < smoke_radius
        covered_all &= covered  # 只有所有角都被遮挡才算遮挡


    total_cover_time = np.sum(covered_all) * (t_list[1] - t_list[0])
    # 打印所有遮挡区间
    if debug:
        intervals = get_cover_intervals(covered_all, t_list)
        for start, end in intervals:
            print(f'遮挡区间: {start:.2f}s ~ {end:.2f}s')
        print(f'总遮挡时间: {total_cover_time:.2f}s')
    return total_cover_time


def get_missile_cover_time_multi(smoke_centers, missile_traj, true_target, smoke_radius, t_list, debug=False):
    """
    smoke_centers: (3, len(t_list), N) 多个烟雾球心轨迹（N为弹数）
    missile_traj: (3, len(t_list)) 导弹轨迹
    true_target: np.array([x, y, z]) 目标点
    smoke_radius: float, 烟雾半径
    t_list: np.array, 时间序列
    返回: 遮挡总时间（float），并打印所有遮挡区间的起止时刻
    """
    T = len(t_list)
    N = smoke_centers.shape[2]
    covered_each = np.zeros((T, N), dtype=bool)
    A = missile_traj.T
    B = np.broadcast_to(true_target, A.shape)
    AB = B - A

    for i in range(N):
        P = smoke_centers[:, :, i].T  # shape (T, 3)
        AP = P - A
        cross = np.cross(AP, AB)
        dist = np.linalg.norm(cross, axis=1) / np.linalg.norm(AB, axis=1)
        t_proj = np.sum(AP * AB, axis=1) / np.sum(AB * AB, axis=1)
        on_segment = (t_proj >= 0) & (t_proj <= 1)
        covered_each[:, i] = (dist < smoke_radius) & on_segment

    # 只要任意一个烟雾球遮挡就算遮挡
    covered = np.any(covered_each, axis=1)

    total_cover_time = np.sum(covered) * (t_list[1] - t_list[0])

    if debug:
        print("每个烟雾球的遮挡时间及区间：")
        for i in range(N):
            single_cover_time = np.sum(covered_each[:, i]) * (t_list[1] - t_list[0])
            print(f"第{i+1}个烟雾球遮挡时间: {single_cover_time:.2f}s", end="下面是各区间：")
            intervals_i = get_cover_intervals(covered_each[:, i], t_list)
            for start, end in intervals_i:
                print(f"    区间: {start:.2f}s ~ {end:.2f}s")
        print("")
        intervals = get_cover_intervals(covered, t_list)
        print("总遮挡区间：")
        for start, end in intervals:
            print(f'    {start:.2f}s ~ {end:.2f}s')
        print(f'总遮挡时间: {total_cover_time:.2f}s')
    return total_cover_time



def get_missile_cover_time_multi_corners(smoke_centers, missile_traj, true_target_corners, smoke_radius, t_list, debug=False):
    """
    smoke_centers: (3, len(t_list), N) 多个烟雾球心轨迹（N为弹数）
    missile_traj: (3, len(t_list)) 导弹轨迹
    true_target_corners: list of 4 np.array([x, y, z]) 目标四个角点
    smoke_radius: float, 烟雾半径
    t_list: np.array, 时间序列
    返回: 遮挡总时间（float），并打印所有遮挡区间的起止时刻
    """
    T = len(t_list)
    N = smoke_centers.shape[2]
    covered_each = np.ones((T, N), dtype=bool)

    A = missile_traj.T

    for i in range(N):
        P = smoke_centers[:, :, i].T  # shape (T, 3)
        covered_corners = np.ones(T, dtype=bool)
        for corner in true_target_corners:
            B = np.broadcast_to(corner, A.shape)
            AB = B - A
            AP = P - A
            cross = np.cross(AP, AB)
            t_proj = np.sum(AP * AB, axis=1) / np.sum(AB * AB, axis=1)
            on_segment = (t_proj >= 0) & (t_proj <= 1)
            dist = np.linalg.norm(cross, axis=1) / np.linalg.norm(AB, axis=1)
            covered = (dist < smoke_radius) & on_segment
            covered_corners &= covered  # 所有角都被遮挡才算
        covered_each[:, i] = covered_corners

    # 只要任意一个烟雾球遮挡所有角就算遮挡
    covered = np.any(covered_each, axis=1)
    total_cover_time = np.sum(covered) * (t_list[1] - t_list[0])

    if debug:
        print("每个烟雾球的遮挡时间及区间（所有角都被遮挡）：")
        for i in range(N):
            single_cover_time = np.sum(covered_each[:, i]) * (t_list[1] - t_list[0])
            print(f"第{i+1}个烟雾球遮挡时间: {single_cover_time:.2f}s", end=" 下面是各区间：")
            intervals_i = get_cover_intervals(covered_each[:, i], t_list)
            for start, end in intervals_i:
                print(f"    区间: {start:.2f}s ~ {end:.2f}s")
        print("")
        intervals = get_cover_intervals(covered, t_list)
        print("总遮挡区间：")
        for start, end in intervals:
            print(f'    {start:.2f}s ~ {end:.2f}s')
        print(f'总遮挡时间: {total_cover_time:.2f}s')
    return total_cover_time



def get_missile_cover_time_multi_bomb_and_missile(smoke_centers, missile_trajs, true_target, smoke_radius, t_list, debug=False):
    """
    smoke_centers: (3, len(t_list), N) 多个烟雾球心轨迹（N为弹数）
    missile_trajs: list of 3 np.ndarray，每个为(3, len(t_list))，三个导弹轨迹
    true_target: np.array([x, y, z]) 目标点
    smoke_radius: float, 烟雾半径
    t_list: np.array, 时间序列
    返回: 所有导弹被遮蔽时间的总和（float），debug时输出每次投弹对每个导弹的遮蔽区间
    """
    T = len(t_list)
    N = smoke_centers.shape[2]
    M = len(missile_trajs)
    # 每个导弹的遮蔽情况
    covered_all_missiles = np.zeros((M, T), dtype=bool)
    covered_each = np.zeros((M, T, N), dtype=bool)

    for m in range(M):
        A = missile_trajs[m].T
        B = np.broadcast_to(true_target, A.shape)
        AB = B - A
        for i in range(N):
            P = smoke_centers[:, :, i].T  # shape (T, 3)
            AP = P - A
            cross = np.cross(AP, AB)
            dist = np.linalg.norm(cross, axis=1) / np.linalg.norm(AB, axis=1)
            t_proj = np.sum(AP * AB, axis=1) / np.sum(AB * AB, axis=1)
            on_segment = (t_proj >= 0) & (t_proj <= 1)
            covered_each[m, :, i] = (dist < smoke_radius) & on_segment
        # 只要任意一个烟雾球遮挡就算遮挡
        covered_all_missiles[m] = np.any(covered_each[m], axis=1)

    # 计算每个导弹被遮蔽的时间
    missile_cover_times = []
    for m in range(M):
        cover_time = np.sum(covered_all_missiles[m]) * (t_list[1] - t_list[0])
        missile_cover_times.append(cover_time)

    total_cover_time = sum(missile_cover_times)

    if debug:
        for m in range(M):
            print(f"导弹{m+1}遮蔽情况：")
            for i in range(N):
                single_cover_time = np.sum(covered_each[m, :, i]) * (t_list[1] - t_list[0])
                print(f"  第{i+1}个烟雾球遮蔽时间: {single_cover_time:.2f}s", end=" 区间：")
                intervals_i = get_cover_intervals(covered_each[m, :, i], t_list)
                for start, end in intervals_i:
                    print(f"    {start:.2f}s ~ {end:.2f}s")
            intervals_m = get_cover_intervals(covered_all_missiles[m], t_list)
            print(f"导弹{m+1}总遮蔽区间：")
            for start, end in intervals_m:
                print(f"    {start:.2f}s ~ {end:.2f}s")
            print(f"导弹{m+1}总遮蔽时间: {missile_cover_times[m]:.2f}s")
        print(f'所有导弹被遮蔽时间总和: {total_cover_time:.2f}s')
    return total_cover_time




# 可视化部分