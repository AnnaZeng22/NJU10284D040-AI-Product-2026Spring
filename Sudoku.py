# 生成数独
import numpy as np
import copy
from typing import List, Tuple, Optional, Dict
import random

def print_sudoku(grid: np.ndarray):
    """打印数独"""
    for i in range(9):
        if i % 3 == 0 and i != 0:
            print("- - - + - - - + - - -")
        row_str = ""
        for j in range(9):
            if j % 3 == 0 and j != 0:
                row_str += "| "
            val = grid[i, j]
            row_str += f"{int(val) if val != 0 else '.'} "
        print(row_str)

class SudokuGenerator:
    """生成数独题目"""
    
    def __init__(self):
        self.grid = np.zeros((9, 9), dtype=int)
    
    def is_valid(self, grid: np.ndarray, row: int, col: int, num: int) -> bool:
        """检查在指定位置放置数字是否有效"""
        # 检查行
        if num in grid[row, :]:
            return False
        # 检查列
        if num in grid[:, col]:
            return False
        # 检查3x3宫格
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        if num in grid[box_row:box_row+3, box_col:box_col+3]:
            return False
        return True
    
    def solve(self, grid: np.ndarray) -> bool:
        """使用回溯法求解数独（用于生成完整解）"""
        for i in range(9):
            for j in range(9):
                if grid[i, j] == 0:
                    nums = list(range(1, 10))
                    random.shuffle(nums)
                    for num in nums:
                        if self.is_valid(grid, i, j, num):
                            grid[i, j] = num
                            if self.solve(grid):
                                return True
                            grid[i, j] = 0
                    return False
        return True
    
    def generate_puzzle(self, difficulty: str = "medium") -> Tuple[np.ndarray, np.ndarray]:
        """
        生成数独题目
        difficulty: "easy", "medium", "hard"
        返回: (题目, 答案)
        """
        # 生成完整解
        self.grid = np.zeros((9, 9), dtype=int)
        self.solve(self.grid)
        solution = self.grid.copy()
        
        # 根据难度决定挖空数量
        if difficulty == "easy":
            cells_to_remove = 35
        elif difficulty == "medium":
            cells_to_remove = 45
        else:  # hard
            cells_to_remove = 55
        
        # 创建题目（挖空）
        puzzle = solution.copy()
        positions = [(i, j) for i in range(9) for j in range(9)]
        random.shuffle(positions)
        
        removed = 0
        for pos in positions:
            if removed >= cells_to_remove:
                break
            i, j = pos
            if puzzle[i, j] != 0:
                # 尝试移除，检查是否仍有唯一解
                temp = puzzle[i, j]
                puzzle[i, j] = 0
                
                # 简单检查：确保该位置只有一个可能的数字
                possible = self.count_possible(puzzle, i, j)
                if possible == 1:
                    removed += 1
                else:
                    puzzle[i, j] = temp
        
        return puzzle, solution
    
    def count_possible(self, grid: np.ndarray, row: int, col: int) -> int:
        """计算某个位置可能的数字数量"""
        count = 0
        for num in range(1, 10):
            if self.is_valid(grid, row, col, num):
                count += 1
        return count

# 生成中等难度数独
generator = SudokuGenerator()
np.random.seed(42)
random.seed(42)
puzzle, solution = generator.generate_puzzle("medium")

print("=" * 50)
print("🎯 中等难度数独题目")
print("=" * 50)
print("\n题目（.表示空格）：")
print_sudoku(puzzle)
print("\n答案（供验证）：")
print_sudoku(solution)

# 用ToT解决数独

import numpy as np
import copy
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field
from heapq import heappush, heappop
import time

@dataclass
class Thought:
    """ToT中的"思维"节点，代表数独求解的一个状态"""
    grid: np.ndarray
    depth: int = 0
    parent: Optional['Thought'] = None
    action: Optional[Tuple[int, int, int]] = None  # (row, col, value)
    confidence: float = 0.0  # 置信度分数
    
    def __hash__(self):
        return hash(self.grid.tobytes())
    
    def __eq__(self, other):
        return np.array_equal(self.grid, other.grid)

class SudokuToTSolver:
    """
    Tree of Thoughts (ToT) 数独求解器
    
    核心思想：
    1. 将数独求解视为一个决策树搜索问题
    2. 每个"思维"节点代表一个数独状态
    3. 使用BFS/Beam Search探索最有希望的路径
    4. 通过启发式评估选择最优分支
    """
    
    def __init__(self, beam_width: int = 3, max_depth: int = 81):
        self.beam_width = beam_width  # Beam Search宽度
        self.max_depth = max_depth
        self.nodes_explored = 0
        self.solution_path = []
        
    def get_possible_values(self, grid: np.ndarray, row: int, col: int) -> List[int]:
        """获取某个空格的所有可能值"""
        if grid[row, col] != 0:
            return []
        
        possible = []
        for num in range(1, 10):
            if self.is_valid_move(grid, row, col, num):
                possible.append(num)
        return possible
    
    def is_valid_move(self, grid: np.ndarray, row: int, col: int, num: int) -> bool:
        """检查移动是否有效"""
        # 检查行
        if num in grid[row, :]:
            return False
        # 检查列
        if num in grid[:, col]:
            return False
        # 检查3x3宫格
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        if num in grid[box_row:box_row+3, box_col:box_col+3]:
            return False
        return True
    
    def find_empty_cells(self, grid: np.ndarray) -> List[Tuple[int, int]]:
        """找到所有空格，按约束程度排序（约束多的优先）"""
        empty = []
        for i in range(9):
            for j in range(9):
                if grid[i, j] == 0:
                    possible = self.get_possible_values(grid, i, j)
                    empty.append((i, j, len(possible)))
        
        # 按可能值数量升序排序（约束多的优先处理）
        empty.sort(key=lambda x: x[2])
        return [(i, j) for i, j, _ in empty]
    
    def calculate_heuristic(self, grid: np.ndarray) -> float:
        """
        启发式评估函数
        评估当前状态的质量，值越小越好
        """
        empty_cells = self.find_empty_cells(grid)
        
        if not empty_cells:
            return 0.0  # 已解决
        
        # 统计约束情况
        total_possibilities = 0
        min_possibilities = 10
        
        for i, j in empty_cells:
            possible = self.get_possible_values(grid, i, j)
            count = len(possible)
            total_possibilities += count
            if count < min_possibilities:
                min_possibilities = count
            
            # 死胡同检测
            if count == 0:
                return float('inf')  # 无效状态
        
        # 启发式分数：综合考虑空格数量和约束强度
        score = len(empty_cells) * 10 + total_possibilities * 0.5 - (10 - min_possibilities) * 2
        return score
    
    def generate_children(self, thought: Thought) -> List[Thought]:
        """
        生成子节点（下一步的所有可能选择）
        使用约束传播和启发式排序
        """
        children = []
        empty_cells = self.find_empty_cells(thought.grid)
        
        if not empty_cells:
            return children
        
        # 选择约束最强的空格（最少可能值）
        row, col = empty_cells[0]
        possible_values = self.get_possible_values(thought.grid, row, col)
        
        # 为每个可能值创建子节点
        for value in possible_values:
            new_grid = thought.grid.copy()
            new_grid[row, col] = value
            
            # 计算置信度（基于约束满足程度）
            confidence = self.calculate_confidence(new_grid, row, col, value)
            
            child = Thought(
                grid=new_grid,
                depth=thought.depth + 1,
                parent=thought,
                action=(row, col, value),
                confidence=confidence
            )
            children.append(child)
        
        # 按置信度排序
        children.sort(key=lambda x: x.confidence, reverse=True)
        return children
    
    def calculate_confidence(self, grid: np.ndarray, row: int, col: int, value: int) -> float:
        """
        计算对某个选择的置信度
        基于该选择对其他格子的约束影响
        """
        confidence = 1.0
        
        # 检查行、列、宫格的约束传播
        # 行约束
        row_empty = sum(1 for j in range(9) if grid[row, j] == 0)
        confidence += (9 - row_empty) * 0.1
        
        # 列约束
        col_empty = sum(1 for i in range(9) if grid[i, col] == 0)
        confidence += (9 - col_empty) * 0.1
        
        # 宫格约束
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        box_empty = sum(1 for i in range(box_row, box_row+3) 
                       for j in range(box_col, box_col+3) if grid[i, j] == 0)
        confidence += (9 - box_empty) * 0.1
        
        # 额外加分：如果该选择使得某些格子只剩下一个可能值
        forced_moves = 0
        temp_grid = grid.copy()
        temp_grid[row, col] = value
        
        for i in range(9):
            for j in range(9):
                if temp_grid[i, j] == 0:
                    possible = self.get_possible_values(temp_grid, i, j)
                    if len(possible) == 1:
                        forced_moves += 1
        
        confidence += forced_moves * 0.5
        
        return confidence
    
    def is_solved(self, grid: np.ndarray) -> bool:
        """检查数独是否已解决"""
        return np.all(grid != 0)
    
    def solve(self, puzzle: np.ndarray) -> Optional[np.ndarray]:
        """
        使用Tree of Thoughts求解数独
        采用Beam Search策略
        """
        start_time = time.time()
        self.nodes_explored = 0
        
        # 初始化根节点
        root = Thought(grid=puzzle.copy(), depth=0)
        
        # Beam Search
        beam = [root]
        visited = set()
        
        while beam:
            new_beam = []
            
            for thought in beam:
                self.nodes_explored += 1
                
                # 检查是否已解决
                if self.is_solved(thought.grid):
                    self.solution_path = self._reconstruct_path(thought)
                    elapsed = time.time() - start_time
                    print(f"✅ 求解成功！")
                    print(f"   探索节点数: {self.nodes_explored}")
                    print(f"   求解路径长度: {len(self.solution_path)}")
                    print(f"   耗时: {elapsed:.4f}秒")
                    return thought.grid
                
                # 生成子节点
                children = self.generate_children(thought)
                
                for child in children:
                    grid_hash = child.grid.tobytes()
                    if grid_hash not in visited:
                        visited.add(grid_hash)
                        new_beam.append(child)
            
            # 按启发式分数排序，保留前beam_width个
            new_beam.sort(key=lambda x: self.calculate_heuristic(x.grid))
            beam = new_beam[:self.beam_width]
            
            # 防止无限循环
            if not beam or all(self.calculate_heuristic(t.grid) == float('inf') for t in beam):
                break
        
        print("❌ 求解失败")
        return None
    
    def _reconstruct_path(self, thought: Thought) -> List[Tuple[int, int, int]]:
        """重建求解路径"""
        path = []
        current = thought
        while current.parent is not None:
            if current.action:
                path.append(current.action)
            current = current.parent
        return list(reversed(path))
    
    def print_solution_steps(self):
        """打印求解步骤"""
        print("\n📋 求解步骤（部分关键步骤）：")
        for i, (row, col, val) in enumerate(self.solution_path[:20]):
            print(f"   步骤{i+1}: 位置({row+1},{col+1}) → 填入 {val}")
        if len(self.solution_path) > 20:
            print(f"   ... 共 {len(self.solution_path)} 步")

# 创建ToT求解器并求解
print("\n" + "=" * 60)
print("🧠 Tree of Thoughts (ToT) 数独求解器")
print("=" * 60)

solver = SudokuToTSolver(beam_width=3)
result = solver.solve(puzzle)

if result is not None:
    print("\n📝 最终解答：")
    print_sudoku(result)
    
    # 验证答案
    if np.array_equal(result, solution):
        print("\n✅ 验证通过！答案正确。")
    else:
        print("\n⚠️ 答案与预期不符，但可能是另一个有效解。")
    
    solver.print_solution_steps()
