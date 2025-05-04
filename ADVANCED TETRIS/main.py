import pygame
import random
import time
import math
from collections import defaultdict

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700
GRID_WIDTH = 10
GRID_HEIGHT = 20
BLOCK_SIZE = 30
GRID_OFFSET_X = (SCREEN_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
GRID_OFFSET_Y = SCREEN_HEIGHT - GRID_HEIGHT * BLOCK_SIZE - 50

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

# Tetrimino shapes with colors
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 1], [1, 0, 0]],  # J
    [[1, 1, 1], [0, 0, 1]],  # L
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]]   # Z
]

SHAPES_COLORS = [CYAN, YELLOW, PURPLE, BLUE, ORANGE, GREEN, RED]

# Game states
MENU = 0
PLAYING = 1
PAUSED = 2
GAME_OVER = 3

class Tetrimino:
    pygame.mixer.init()  # Initialize the sound mixer
    def __init__(self, shape_idx, x=GRID_WIDTH // 2 - 2, y=0):
        self.shape = SHAPES[shape_idx]
        self.color = SHAPES_COLORS[shape_idx]
        self.x = x
        self.y = y
        self.rotation = 0
        self.shape_idx = shape_idx
        # Add these cooldown attributes:
        self.last_move_time = 0
        self.last_rotate_time = 0
        self.move_cooldown = 0.1  # seconds between moves
        self.rotate_cooldown = 0.2  # seconds between rotations
        self.last_drop_time = 0
        self.lock_delay = 0.5
        self.lock_timer = 0
        self.locking = False
        self.t_spin = False
    def rotate(self, grid):
        """Rotate the tetrimino clockwise with wall kicks and T-spin detection"""
        original_rotation = self.rotation
        original_shape = self.shape
        
        # Rotate the shape
        self.rotation = (self.rotation + 1) % 4
        self.shape = [list(row) for row in zip(*self.shape[::-1])]
        
        # Wall kick tests (5 tests for each rotation)
        kick_offsets = [
            [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],  # 0->1
            [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],      # 1->2
            [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],      # 2->3
            [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)]     # 3->0
        ]
        
        # Try each offset in the current rotation's kick table
        for dx, dy in kick_offsets[original_rotation]:
            self.x += dx
            self.y += dy
            
            if not self.collision(grid):
                # Check for T-spin conditions
                if self.shape_idx == 2:  # T piece
                    corners = 0
                    test_positions = [
                        (self.x, self.y),
                        (self.x + len(self.shape[0]) - 1, self.y),
                        (self.x, self.y + len(self.shape) - 1),
                        (self.x + len(self.shape[0]) - 1, self.y + len(self.shape) - 1)
                    ]
                    
                    for tx, ty in test_positions:
                        if (tx < 0 or tx >= GRID_WIDTH or ty >= GRID_HEIGHT or 
                            (ty >= 0 and grid[ty][tx] is not None)):
                            corners += 1
                    
                    # T-spin if 3 or more corners are filled and last move was rotation
                    self.t_spin = (corners >= 3 and 
                                  time.time() - self.last_rotate_time < 0.1)
                
                self.last_rotate_time = time.time()
                return True
            
            # Revert the offset if it didn't work
            self.x -= dx
            self.y -= dy
        
        # If all kicks failed, revert rotation
        self.rotation = original_rotation
        self.shape = original_shape
        return False
    
    def move(self, dx, dy, grid):
        """Move the tetrimino by dx, dy if possible"""
        self.x += dx
        self.y += dy
        
        if self.collision(grid):
            self.x -= dx
            self.y -= dy
            return False
        
        self.last_move_time = time.time()
        
        # Reset lock timer if movement was successful
        if dy != 0:  # Only reset on downward movement
            self.locking = False
            self.lock_timer = 0
        
        return True
    
    def hard_drop(self, grid):
        """Drop the piece instantly to the lowest possible position"""
        while self.move(0, 1, grid):
            pass
        self.locking = True
        self.lock_timer = self.lock_delay
        self.last_drop_time = time.time()
    
    def collision(self, grid):
        """Check if the tetrimino collides with walls or other blocks"""
        for y, row in enumerate(self.shape):
            for x, cell in enumerate(row):
                if cell:
                    board_x = self.x + x
                    board_y = self.y + y
                    
                    if (board_x < 0 or board_x >= GRID_WIDTH or 
                        board_y >= GRID_HEIGHT or 
                        (board_y >= 0 and grid[board_y][board_x] is not None)):
                        return True
        return False
    
    def update_lock_timer(self, dt):
        """Update the lock timer based on time passed"""
        if self.locking:
            self.lock_timer += dt
            if self.lock_timer >= self.lock_delay:
                return True
        return False
    
    def draw(self, screen, ghost=False):
        """Draw the tetrimino on the screen"""
        color = self.color
        alpha = 100 if ghost else 255
        s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
        s.fill((color[0], color[1], color[2], alpha))
        
        for y, row in enumerate(self.shape):
            for x, cell in enumerate(row):
                if cell:
                    pos_x = GRID_OFFSET_X + (self.x + x) * BLOCK_SIZE
                    pos_y = GRID_OFFSET_Y + (self.y + y) * BLOCK_SIZE
                    
                    if ghost:
                        # Draw ghost piece outline
                        pygame.draw.rect(screen, color, 
                                        (pos_x, pos_y, BLOCK_SIZE, BLOCK_SIZE), 1)
                    else:
                        screen.blit(s, (pos_x, pos_y))
                        pygame.draw.rect(screen, WHITE, 
                                        (pos_x, pos_y, BLOCK_SIZE, BLOCK_SIZE), 1)

class TetrisGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Advanced Tetris")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 24)
        self.big_font = pygame.font.SysFont('Arial', 48)
        
        self.reset_game()

    def reset_game(self):
         """Reset the game state"""
         self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
         self.bag = list(range(len(SHAPES)))  # Initialize the bag first
         random.shuffle(self.bag)  # Then shuffle it
         self.current_piece = self.new_piece()
         self.next_pieces = [self.new_piece() for _ in range(5)]
         self.held_piece = None
         self.can_hold = True
         self.score = 0
         self.level = 1
         self.lines_cleared = 0
         self.combo = -1
         self.game_state = MENU
         self.last_clear_time = 0
         self.gravity = self.calculate_gravity()
         self.drop_timer = 0
         self.piece_count = 0
         self.b2b = False  # Back-to-back flag
        
    
        
    def new_piece(self):
        """Create a new tetrimino using the 7-bag randomization system"""
        if not self.bag:
            self.bag = list(range(len(SHAPES)))
            random.shuffle(self.bag)
        
        shape_idx = self.bag.pop()
        return Tetrimino(shape_idx)
    
    def calculate_gravity(self):
     """Fixed slow falling speed (ignores level)"""
     return 0.5  # Smaller = slower
    
    def hold_piece(self):
        """Hold the current piece"""
        if not self.can_hold:
            return
        
        if self.held_piece is None:
            self.held_piece = Tetrimino(self.current_piece.shape_idx)
            self.current_piece = self.next_pieces.pop(0)
            self.next_pieces.append(self.new_piece())
        else:
            # Swap current piece with held piece
            held_idx = self.held_piece.shape_idx
            self.held_piece = Tetrimino(self.current_piece.shape_idx)
            self.current_piece = Tetrimino(held_idx)
        
        self.can_hold = False
        self.current_piece.x = GRID_WIDTH // 2 - len(self.current_piece.shape[0]) // 2
        self.current_piece.y = 0
    
    def clear_lines(self):
        """Clear completed lines and calculate score"""
        lines_to_clear = []
        for y in range(GRID_HEIGHT):
            if all(self.grid[y]):
                lines_to_clear.append(y)
        
        if not lines_to_clear:
            self.combo = -1
            return 0
        
        # Calculate score based on lines cleared, level, and special conditions
        line_scores = {1: 100, 2: 300, 3: 500, 4: 800}
        base_score = line_scores.get(len(lines_to_clear), 0) * self.level
        
        # T-spin bonus
        if self.current_piece.t_spin:
            if len(lines_to_clear) == 0:
                base_score = 400 * self.level
            elif len(lines_to_clear) == 1:
                base_score = 800 * self.level
            elif len(lines_to_clear) == 2:
                base_score = 1200 * self.level
            self.b2b = True
        
        # Back-to-back bonus
        if len(lines_to_clear) >= 4 or (self.current_piece.t_spin and len(lines_to_clear) > 0):
            if self.b2b:
                base_score = base_score * 3 // 2
            self.b2b = True
        elif len(lines_to_clear) > 0:
            self.b2b = False
        
        # Combo bonus
        if self.combo >= 0:
            base_score += 50 * self.combo * self.level
        
        self.score += base_score
        self.combo += 1
        self.lines_cleared += len(lines_to_clear)
        
        # Update level (every 10 lines)
        self.level = self.lines_cleared // 10 + 1
        self.gravity = self.calculate_gravity()
        
        # Remove cleared lines and add new empty ones at the top
        for y in sorted(lines_to_clear):
            del self.grid[y]
            self.grid.insert(0, [None for _ in range(GRID_WIDTH)])
        
        self.last_clear_time = time.time()
        return len(lines_to_clear)
    
    def get_ghost_position(self):
        """Calculate where the piece would land if hard dropped"""
        ghost = Tetrimino(self.current_piece.shape_idx, 
                         self.current_piece.x, self.current_piece.y)
        while not ghost.collision(self.grid):
            ghost.y += 1
        ghost.y -= 1
        return ghost
    
    def lock_piece(self):
        """Lock the current piece into the grid"""
        for y, row in enumerate(self.current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    board_y = self.current_piece.y + y
                    board_x = self.current_piece.x + x
                    if 0 <= board_y < GRID_HEIGHT and 0 <= board_x < GRID_WIDTH:
                        self.grid[board_y][board_x] = self.current_piece.color
        
        lines_cleared = self.clear_lines()
        
        # Check for game over
        if any(self.grid[0]):
            self.game_state = GAME_OVER
            return
        
        self.current_piece = self.next_pieces.pop(0)
        self.next_pieces.append(self.new_piece())
        self.can_hold = True
        self.piece_count += 1
        
        # Reset position
        self.current_piece.x = GRID_WIDTH // 2 - len(self.current_piece.shape[0]) // 2
        self.current_piece.y = 0
    
    def draw_grid(self):
        """Draw the game grid and borders"""
        # Draw grid background
        pygame.draw.rect(self.screen, GRAY, 
                         (GRID_OFFSET_X - 2, GRID_OFFSET_Y - 2, 
                          GRID_WIDTH * BLOCK_SIZE + 4, GRID_HEIGHT * BLOCK_SIZE + 4), 0)
        
        # Draw grid cells
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.grid[y][x] is not None:
                    pygame.draw.rect(self.screen, self.grid[y][x], 
                                    (GRID_OFFSET_X + x * BLOCK_SIZE, 
                                     GRID_OFFSET_Y + y * BLOCK_SIZE, 
                                     BLOCK_SIZE, BLOCK_SIZE))
                    pygame.draw.rect(self.screen, WHITE, 
                                    (GRID_OFFSET_X + x * BLOCK_SIZE, 
                                     GRID_OFFSET_Y + y * BLOCK_SIZE, 
                                     BLOCK_SIZE, BLOCK_SIZE), 1)
        
        # Draw grid lines
        for x in range(GRID_WIDTH + 1):
            pygame.draw.line(self.screen, (50, 50, 50), 
                            (GRID_OFFSET_X + x * BLOCK_SIZE, GRID_OFFSET_Y), 
                            (GRID_OFFSET_X + x * BLOCK_SIZE, GRID_OFFSET_Y + GRID_HEIGHT * BLOCK_SIZE))
        
        for y in range(GRID_HEIGHT + 1):
            pygame.draw.line(self.screen, (50, 50, 50), 
                            (GRID_OFFSET_X, GRID_OFFSET_Y + y * BLOCK_SIZE), 
                            (GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE, GRID_OFFSET_Y + y * BLOCK_SIZE))
    
    def draw_info_panel(self):
        """Draw the side panel with game information"""
        # Next pieces
        next_text = self.font.render("NEXT:", True, WHITE)
        self.screen.blit(next_text, (GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE + 30, 50))
        
        for i, piece in enumerate(self.next_pieces[:5]):
            for y, row in enumerate(piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        pos_x = GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE + 50 + x * BLOCK_SIZE
                        pos_y = 100 + i * 100 + y * BLOCK_SIZE
                        pygame.draw.rect(self.screen, piece.color, 
                                        (pos_x, pos_y, BLOCK_SIZE, BLOCK_SIZE))
                        pygame.draw.rect(self.screen, WHITE, 
                                        (pos_x, pos_y, BLOCK_SIZE, BLOCK_SIZE), 1)
        
        # Held piece
        hold_text = self.font.render("HOLD:", True, WHITE)
        self.screen.blit(hold_text, (GRID_OFFSET_X - 150, 50))
        
        if self.held_piece:
            for y, row in enumerate(self.held_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        pos_x = GRID_OFFSET_X - 130 + x * BLOCK_SIZE
                        pos_y = 100 + y * BLOCK_SIZE
                        pygame.draw.rect(self.screen, self.held_piece.color, 
                                        (pos_x, pos_y, BLOCK_SIZE, BLOCK_SIZE))
                        pygame.draw.rect(self.screen, WHITE, 
                                        (pos_x, pos_y, BLOCK_SIZE, BLOCK_SIZE), 1)
        
        # Score and level
        score_text = self.font.render(f"SCORE: {self.score}", True, WHITE)
        level_text = self.font.render(f"LEVEL: {self.level}", True, WHITE)
        lines_text = self.font.render(f"LINES: {self.lines_cleared}", True, WHITE)
        
        self.screen.blit(score_text, (GRID_OFFSET_X - 150, 250))
        self.screen.blit(level_text, (GRID_OFFSET_X - 150, 300))
        self.screen.blit(lines_text, (GRID_OFFSET_X - 150, 350))
        
        # Combo
        if self.combo > 0:
            combo_text = self.font.render(f"COMBO: {self.combo}", True, WHITE)
            self.screen.blit(combo_text, (GRID_OFFSET_X - 150, 400))
        
        # T-spin indicator
        if self.current_piece.t_spin:
            tspin_text = self.font.render("T-SPIN!", True, YELLOW)
            self.screen.blit(tspin_text, (GRID_OFFSET_X - 150, 450))
        
        # Back-to-back indicator
        if self.b2b:
            b2b_text = self.font.render("B2B", True, ORANGE)
            self.screen.blit(b2b_text, (GRID_OFFSET_X - 150, 500))
    
    def draw_menu(self):
        """Draw the main menu"""
        title = self.big_font.render("ADVANCED TETRIS", True, WHITE)
        start_text = self.font.render("Press ENTER to Start", True, WHITE)
        controls_text1 = self.font.render("Controls:", True, WHITE)
        controls_text2 = self.font.render("Left/Right: Move", True, WHITE)
        controls_text3 = self.font.render("Up: Rotate", True, WHITE)
        controls_text4 = self.font.render("Down: Soft Drop", True, WHITE)
        controls_text5 = self.font.render("Space: Hard Drop", True, WHITE)
        controls_text6 = self.font.render("C: Hold", True, WHITE)
        controls_text7 = self.font.render("P: Pause", True, WHITE)
        
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        self.screen.blit(start_text, (SCREEN_WIDTH // 2 - start_text.get_width() // 2, 300))
        self.screen.blit(controls_text1, (SCREEN_WIDTH // 2 - controls_text1.get_width() // 2, 400))
        self.screen.blit(controls_text2, (SCREEN_WIDTH // 2 - controls_text2.get_width() // 2, 450))
        self.screen.blit(controls_text3, (SCREEN_WIDTH // 2 - controls_text3.get_width() // 2, 480))
        self.screen.blit(controls_text4, (SCREEN_WIDTH // 2 - controls_text4.get_width() // 2, 510))
        self.screen.blit(controls_text5, (SCREEN_WIDTH // 2 - controls_text5.get_width() // 2, 540))
        self.screen.blit(controls_text6, (SCREEN_WIDTH // 2 - controls_text6.get_width() // 2, 570))
        self.screen.blit(controls_text7, (SCREEN_WIDTH // 2 - controls_text7.get_width() // 2, 600))
    
    def draw_pause(self):
        """Draw the pause screen"""
        pause_text = self.big_font.render("PAUSED", True, WHITE)
        continue_text = self.font.render("Press P to Continue", True, WHITE)
        
        # Semi-transparent overlay
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))
        self.screen.blit(s, (0, 0))
        
        self.screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        self.screen.blit(continue_text, (SCREEN_WIDTH // 2 - continue_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
    
    def draw_game_over(self):
        """Draw the game over screen"""
        over_text = self.big_font.render("GAME OVER", True, RED)
        score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        restart_text = self.font.render("Press ENTER to Restart", True, WHITE)
        
        # Semi-transparent overlay
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        
        self.screen.blit(over_text, (SCREEN_WIDTH // 2 - over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
        self.screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 100))
    
    def update(self, dt):
        """Update game state"""
        if self.game_state == PLAYING:
            # Apply gravity
            self.drop_timer += dt
            if self.drop_timer >= self.gravity:
                if not self.current_piece.move(0, 1, self.grid):
                    # Piece can't move down - start lock delay
                    self.current_piece.locking = True
                self.drop_timer = 0
            
            # Check if piece should lock
            if self.current_piece.update_lock_timer(dt):
                self.lock_piece()
    
    def draw(self):
        """Draw everything"""
        self.screen.fill(BLACK)
        
        if self.game_state == MENU:
            self.draw_menu()
        elif self.game_state == GAME_OVER:
            self.draw_grid()
            self.draw_info_panel()
            self.draw_game_over()
        else:
            self.draw_grid()
            self.draw_info_panel()
            
            # Draw ghost piece
            ghost = self.get_ghost_position()
            ghost.draw(self.screen, ghost=True)
            
            # Draw current piece
            self.current_piece.draw(self.screen)
            
            if self.game_state == PAUSED:
                self.draw_pause()
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        running = True
        last_time = time.time()
        
        while running:
            current_time = time.time() 
            dt = current_time - last_time
            last_time = current_time
            
            for event in pygame.event.get():
             if event.type == pygame.QUIT:
                 running = False
             elif event.type == pygame.KEYDOWN:
                 current_time = time.time()
                 # Left Movement
                 if event.key == pygame.K_LEFT:
                     if current_time - self.current_piece.last_move_time > self.current_piece.move_cooldown:
                         self.current_piece.move(-1, 0, self.grid)
                         self.current_piece.last_move_time = current_time
                         try:
                             pygame.mixer.Sound(buffer=bytearray([64] * 500)).play()  # Low-pitched
                         except:
                             pass
                 # Right Movement        
                 elif event.key == pygame.K_RIGHT:
                     if current_time - self.current_piece.last_move_time > self.current_piece.move_cooldown:
                         self.current_piece.move(1, 0, self.grid)
                         self.current_piece.last_move_time = current_time
                         try:
                             pygame.mixer.Sound(buffer=bytearray([64] * 500)).play()  # Low-pitched
                         except:
                             pass
                 # Rotation
                 elif event.key == pygame.K_UP:
                     if current_time - self.current_piece.last_rotate_time > self.current_piece.rotate_cooldown:
                         self.current_piece.rotate(self.grid)
                         self.current_piece.last_rotate_time = current_time
                         try:
                             pygame.mixer.Sound(buffer=bytearray([128] * 1000)).play()  # Mid-pitched
                         except:
                             pass
                 # Soft Drop (Down Key)
                 elif event.key == pygame.K_DOWN:
                     if current_time - self.current_piece.last_move_time > self.current_piece.move_cooldown:
                         self.current_piece.move(0, 1, self.grid)
                         self.current_piece.last_move_time = current_time
                         try:
                             pygame.mixer.Sound(buffer=bytearray([150] * 800)).play()  # Higher-pitched
                         except:
                             pass
                 # Hard Drop (Space)
                 elif event.key == pygame.K_SPACE:
                     self.current_piece.hard_drop(self.grid)
                     try:
                         pygame.mixer.Sound(buffer=bytearray([200] * 1500)).play()  # Loudest/longest
                     except:
                         pass
                 # ... rest of your key handling code
                 elif event.key == pygame.K_c:
                     self.hold_piece() # Hold current piece
                 elif event.key == pygame.K_p:
                     if self.game_state == PLAYING:
                         self.game_state = PAUSED
                     elif self.game_state == PAUSED:
                         self.game_state = PLAYING
                 elif event.key == pygame.K_RETURN:
                     if self.game_state == MENU or self.game_state == GAME_OVER:
                         if self.game_state == GAME_OVER:
                             self.reset_game() # Reset game state
                         self.game_state = PLAYING   
                    
                          
            
            self.update(dt)
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    game = TetrisGame()
    game.run()