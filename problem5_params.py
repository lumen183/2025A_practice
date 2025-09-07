import sys
import os
from contextlib import contextmanager

# 定义一个上下文管理器，用于临时重定向输出
@contextmanager
def redirect_output(log_file="output.log"):
    # 保存原始stdout
    original_stdout = sys.stdout
    # 打开日志文件（追加模式，确保中断后内容不丢失）
    with open(log_file, 'a', encoding='utf-8') as f:
        # 定义同时输出到控制台和文件的类
        class MultiOutput:
            def write(self, message):
                original_stdout.write(message)  # 输出到控制台
                f.write(message)                # 写入文件
                f.flush()                       # 立即刷新到磁盘
                original_stdout.flush()
            
            def flush(self):
                original_stdout.flush()
                f.flush()
        
        # 重定向全局stdout
        sys.stdout = MultiOutput()
        try:
            yield  # 执行被包裹的代码
        finally:
            # 恢复原始stdout
            sys.stdout = original_stdout

# ----------------------
# 你的原有代码（放在下面）
# ----------------------

print("测试")
from calc_cover_time import *
from scipy.optimize import dual_annealing

missile_starts = [
    np.array([20000, 0, 2000]),
    np.array([19000, 600, 2100]),
    np.array([18000, -600, 1900])
]

bounds_range = [
    [(130,140),   (np.pi/2, np.pi*3/2), (0,13.87), (1,13.87), (2, 13.87),     (0,18.97),(0,18.97),(0,18.97),   ],
    [(70, 140),   (np.pi, np.pi*2),     (0, 50),   (1,50),    (2,50),         (0,16.74),(0, 16.74),(0, 16.74), ],
    [(70, 140),   (0, np.pi),           (0,60),    (1,60),    (2,60),         (0, 11.9),(0, 11.9),(0, 11.9),   ],
    [(70, 140),   (np.pi, np.pi*2),     (0, 56),   (0, 56),   (0, 56),        (0, 18.97),(0, 18.97),(0, 18.97),],
    [(70, 140),   (0, np.pi),           (0, 43.7), (1, 43.7), (2, 43.7),      (0,16.12),(0,16.12),(0,16.12),   ],
]

drone_pos = {
    0: np.array([17800,0,1800]),
    1: np.array([12000,1400,1400]),
    2: np.array([6000,-3000,700]),
    3: np.array([11000,2000,1800]),
    4: np.array([13000,-2000,1300])
}

missile_trajs = [get_missile_traj(missile_starts[i], fake_target, v_M1, t_list) for i in range(3)]

# 使用上下文管理器包裹整个程序逻辑，确保所有print被捕获
with redirect_output("output.log"):
    while True:
        for idx in range(1,5):
            def sa_objective_multi(x):
                try:
                    speed = x[0]
                    direction_angle = x[1]
                    throw_times = x[2:5]
                    burst_delays = x[5:8]
                    smoke_centers = get_smoke_center_multi(drone_pos[idx], direction_angle, speed, throw_times, burst_delays, t_list)
                    cover_time = get_missile_cover_time_multi_bomb_and_missile(smoke_centers, missile_trajs, true_target, smoke_R, t_list)
                    return -cover_time
                except AssertionError:
                    return 1e6

            bounds = bounds_range[idx]
            max_iter = 6000

            result = dual_annealing(
                sa_objective_multi,
                bounds,
                maxiter=max_iter,
                seed=42,
                initial_temp=20000,
            )
            
            print(f"以下为第{idx+1}架无人机的结果")
            print("最优参数:", result.x)
            print("最大遮挡总时间:", -result.fun)
            print("")

            # 函数内部的print也会被捕获到文件中
            smoke_centers01 = get_smoke_center_multi(drone_pos[idx], result.x[1], result.x[0], result.x[2:5], result.x[5:8], t_list)
            get_missile_cover_time_multi_bomb_and_missile(smoke_centers01, missile_trajs, true_target, smoke_R, t_list, debug=True)
    