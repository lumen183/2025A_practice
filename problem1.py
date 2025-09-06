import numpy as np
import matplotlib.pyplot as plt
# 设置matplotlib中文字体
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC", "sans-serif"]
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 问题1：烟幕干扰弹的有效遮蔽时长计算

def calculate_effective_shielding_duration():
    """
    计算烟幕干扰弹对M1导弹的有效遮蔽时长
    根据问题描述：
    - 无人机FY1以120m/s朝向假目标方向飞行
    - 受领任务1.5s后投放1枚烟幕干扰弹
    - 间隔3.6s后起爆
    - 烟幕云团中心10m范围内在起爆20s内提供有效遮蔽
    - 烟幕云团以3m/s匀速下沉
    - 真目标视为质点，位置为(0, 200, 5)（原圆柱体中心点）
    """
    # 初始化参数
    # 位置信息（以假目标为原点，xyz坐标系）
    m1_initial = np.array([20000, 0, 2000])  # 导弹M1初始位置
    fake_target = np.array([0, 0, 0])         # 假目标位置
    fy1_initial = np.array([17800, 0, 1800])  # 无人机FY1初始位置
    
    # 真目标参数（视为质点）
    target_point = np.array([0, 200, 5])  # 质点位置（原圆柱体中心点）
    
    # 运动参数
    missile_speed = 300  # 导弹速度(m/s)
    uav_speed = 120      # 无人机速度(m/s)
    smoke_sink_speed = 3 # 烟幕下沉速度(m/s)
    release_time = 1.5   # 投放时间(s)（受领任务后）
    burst_delay = 3.6    # 起爆延迟(s)（投放后）
    effective_radius = 10  # 有效遮蔽半径(m)
    effective_time = 20   # 有效遮蔽时间(s)
    gravity = 9.80665    # 重力加速度(m/s²)
    
    # 计算无人机飞行方向向量（朝向假目标）
    uav_dir = fake_target - fy1_initial
    uav_dir = uav_dir / np.linalg.norm(uav_dir)  # 单位化
    # 由于是等高飞行，z分量应为0
    uav_dir[2] = 0
    uav_dir = uav_dir / np.linalg.norm(uav_dir)  # 重新单位化
    
    # 计算导弹飞行方向向量（朝向假目标）
    missile_dir = fake_target - m1_initial
    missile_dir = missile_dir / np.linalg.norm(missile_dir)  # 单位化
    
    # 计算投放时无人机的位置
    fy1_release_pos = fy1_initial + uav_speed * release_time * uav_dir
    
    # 计算烟幕弹投放后到起爆前的运动（自由落体）
    # 烟幕弹脱离无人机后做平抛运动，水平方向速度等于无人机速度，竖直方向自由落体
    # 水平方向位移
    smoke_horizontal_displacement = uav_speed * burst_delay * uav_dir
    # 竖直方向位移（自由落体）
    smoke_vertical_displacement = 0.5 * gravity * burst_delay**2
    # 起爆时烟幕弹的位置
    smoke_burst_pos = fy1_release_pos + smoke_horizontal_displacement
    smoke_burst_pos[2] -= smoke_vertical_displacement  # 竖直方向向下位移
    print(f"烟幕起爆位置: {smoke_burst_pos}")
    
    # 时间步长（用于模拟）
    time_step = 0.001  # 减小时间步长以提高精度
    effective_duration = 0
    
    # 遮挡状态跟踪变量
    is_shielding = False
    start_time = None
    end_time = None
    shielding_intervals = []
    
    # 存储距离数据用于可视化
    time_data = []
    distance_data = []
    
    # 模拟烟幕有效时间内的情况（起爆后20s）
    for t in np.arange(0, effective_time, time_step):
        # 计算当前时间烟幕云团中心位置（匀速下沉）
        smoke_current_pos = smoke_burst_pos.copy()
        smoke_current_pos[2] -= smoke_sink_speed * t
        
        # 计算当前时间导弹位置
        # 导弹飞行时间 = 受领任务时间 + 投放时间 + 起爆延迟 + 当前模拟时间
        missile_flight_time = release_time + burst_delay + t
        missile_current_pos = m1_initial + missile_speed * missile_flight_time * missile_dir
        
        # 判断烟幕是否有效遮蔽（阻挡导弹到真目标质点的视线）
        # 线段：导弹位置到目标质点
        line_start = missile_current_pos
        line_end = target_point
        line_vec = line_end - line_start
        line_length_squared = np.dot(line_vec, line_vec)
        
        if line_length_squared == 0:
            # 导弹与目标重合
            distance = np.linalg.norm(smoke_current_pos - line_start)
            current_shielded = distance <= effective_radius
        else:
            # 计算烟幕中心到线段的最短距离
            t_proj = np.dot(smoke_current_pos - line_start, line_vec) / line_length_squared
            if t_proj < 0:
                closest_point_on_line = line_start
            elif t_proj > 1:
                closest_point_on_line = line_end
            else:
                closest_point_on_line = line_start + t_proj * line_vec
            distance = np.linalg.norm(smoke_current_pos - closest_point_on_line)
            current_shielded = distance <= effective_radius
        
        # 记录距离数据
        time_data.append(t)
        distance_data.append(distance)
        
        # 检测遮挡状态变化
        if current_shielded and not is_shielding:
            # 开始遮挡
            start_time = t
            is_shielding = True
        elif not current_shielded and is_shielding:
            # 结束遮挡
            end_time = t
            shielding_intervals.append((start_time, end_time))
            is_shielding = False
        
        if current_shielded:
            effective_duration += time_step
    
    # 处理模拟结束时仍在遮挡的情况
    if is_shielding:
        shielding_intervals.append((start_time, effective_time))
    
    return effective_duration, shielding_intervals, time_data, distance_data, effective_radius

# 执行计算并输出结果
effective_shielding_time, shielding_intervals, time_data, distance_data, effective_radius = calculate_effective_shielding_duration()
print(f"烟幕干扰弹对M1的有效遮蔽时长：{effective_shielding_time:.4f} 秒")

# 输出遮挡起止点
if shielding_intervals:
    print("遮挡起止时间（相对于烟幕起爆时刻，单位：秒）：")
    for i, (start, end) in enumerate(shielding_intervals):
        print(f"  区间 {i+1}: 开始 = {start:.4f}, 结束 = {end:.4f}, 持续时间 = {end-start:.4f}")
else:
    print("没有发生有效遮挡")

# 输出距离数据的部分示例
print("\n距离数据示例（前5个时间点）：")
for i in range(min(5, len(time_data))):
    print(f"时间: {time_data[i]:.4f}秒, 距离: {distance_data[i]:.4f}米")

# 可视化距离随时间变化
plt.figure(figsize=(10, 6))
plt.plot(time_data, distance_data, 'b-', label='烟幕中心到导弹-目标线段的距离')
plt.axhline(y=effective_radius, color='r', linestyle='--', label=f'有效遮蔽半径 ({effective_radius}m)')

# 标记遮挡区间
for start, end in shielding_intervals:
    plt.axvspan(start, end, color='green', alpha=0.2)

plt.xlabel('时间 (秒)')
plt.ylabel('距离 (米)')
plt.title('烟幕干扰弹距离变化与有效遮挡区间')
plt.legend()
plt.grid(True)
plt.savefig('smoke_shielding_visualization.png', dpi=300)
print("\n可视化图像已保存为 'smoke_shielding_visualization.png'")
# 非交互式环境下避免显示图像窗口
plt.close()