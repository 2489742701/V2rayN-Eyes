from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # 创建256x256的图像
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 定义颜色
    earth_blue = (30, 144, 255)
    earth_green = (34, 139, 34)
    v_color = (255, 255, 255)
    v_outline = (0, 0, 139)
    
    # 绘制地球背景（蓝色圆形）
    earth_center = (size // 2, size // 2)
    earth_radius = 80
    draw.ellipse(
        [earth_center[0] - earth_radius, earth_center[1] - earth_radius,
         earth_center[0] + earth_radius, earth_center[1] + earth_radius],
        fill=earth_blue, outline=(0, 100, 200), width=3
    )
    
    # 绘制一些陆地（绿色椭圆）
    # 美洲
    draw.ellipse([earth_center[0] - 50, earth_center[1] - 40,
                  earth_center[0] - 20, earth_center[1] + 10],
                 fill=earth_green, outline=(20, 100, 20), width=1)
    # 欧亚
    draw.ellipse([earth_center[0] + 10, earth_center[1] - 50,
                  earth_center[0] + 60, earth_center[1] - 10],
                 fill=earth_green, outline=(20, 100, 20), width=1)
    # 非洲
    draw.ellipse([earth_center[0] + 5, earth_center[1] + 5,
                  earth_center[0] + 35, earth_center[1] + 45],
                 fill=earth_green, outline=(20, 100, 20), width=1)
    
    # 绘制经纬线
    for i in range(3):
        y = earth_center[1] - earth_radius + (i + 1) * (earth_radius * 2 // 4)
        draw.arc([earth_center[0] - earth_radius, y - 2,
                  earth_center[0] + earth_radius, y + 2],
                 0, 360, fill=(200, 200, 200), width=1)
    
    for i in range(3):
        x = earth_center[0] - earth_radius + (i + 1) * (earth_radius * 2 // 4)
        draw.arc([x - 2, earth_center[1] - earth_radius,
                  x + 2, earth_center[1] + earth_radius],
                 0, 180, fill=(200, 200, 200), width=1)
    
    # 绘制字母V（在地球前面）
    v_size = 120
    v_center_x = size // 2
    v_center_y = size // 2
    
    # V的轮廓
    v_points = [
        (v_center_x - 50, v_center_y - 40),
        (v_center_x, v_center_y + 40),
        (v_center_x + 50, v_center_y - 40)
    ]
    
    # 绘制V的填充（白色）
    draw.polygon(v_points, fill=v_color)
    
    # 绘制V的边框
    draw.line([v_points[0], v_points[1]], fill=v_outline, width=4)
    draw.line([v_points[1], v_points[2]], fill=v_outline, width=4)
    
    # 添加一些装饰效果
    # 在V上添加渐变效果
    for i in range(10):
        y_offset = -40 + i * 8
        width = 100 - i * 5
        draw.ellipse([v_center_x - width//2, v_center_y + y_offset - 2,
                      v_center_x + width//2, v_center_y + y_offset + 2],
                     fill=(255, 255, 255, 50))
    
    # 保存为PNG
    img.save('v2ray_icon.png', 'PNG')
    print("✅ 已生成 v2ray_icon.png")
    
    # 尝试转换为ICO格式
    try:
        # 创建不同尺寸的ICO
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icon_images = []
        for s in sizes:
            resized = img.resize(s, Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # 保存为ICO
        icon_images[0].save('v2ray_icon.ico', format='ICO', sizes=sizes)
        print("✅ 已生成 v2ray_icon.ico")
    except Exception as e:
        print(f"⚠️ 生成ICO文件失败: {e}")
    
    # 保存为其他尺寸的PNG
    for s in [(32, 32), (48, 48), (64, 64), (128, 128)]:
        resized = img.resize(s, Image.Resampling.LANCZOS)
        resized.save(f'v2ray_icon_{s[0]}x{s[1]}.png', 'PNG')
        print(f"✅ 已生成 v2ray_icon_{s[0]}x{s[1]}.png")

if __name__ == '__main__':
    try:
        create_icon()
        print("\n🎉 图标生成完成！")
        print("生成的文件：")
        print("  - v2ray_icon.png (256x256)")
        print("  - v2ray_icon.ico (多尺寸)")
        print("  - v2ray_icon_32x32.png")
        print("  - v2ray_icon_48x48.png")
        print("  - v2ray_icon_64x64.png")
        print("  - v2ray_icon_128x128.png")
    except ImportError:
        print("❌ 错误：未安装Pillow库")
        print("请运行: pip install Pillow")
    except Exception as e:
        print(f"❌ 生成图标失败: {e}")
