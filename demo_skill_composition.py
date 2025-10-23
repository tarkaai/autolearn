"""Demonstration of skill composition - skills calling other skills.

This script demonstrates the new skill composition feature where skills
can call other skills using the call_skill() function.
"""

from backend.skill_engine import SkillEngine, SkillMeta


def demo_basic_composition():
    """Demonstrate basic skill composition."""
    print("=" * 60)
    print("DEMO: Basic Skill Composition")
    print("=" * 60)
    
    engine = SkillEngine()
    
    # Create a simple calculator skill
    calculator_code = """
def calculator(operation: str, a: float, b: float) -> dict:
    \"\"\"Basic calculator that can add or multiply.\"\"\"
    if operation == 'add':
        return {'result': a + b, 'operation': 'addition'}
    elif operation == 'multiply':
        return {'result': a * b, 'operation': 'multiplication'}
    else:
        return {'error': f'Unknown operation: {operation}'}
"""
    
    calculator_meta = SkillMeta(
        name="calculator",
        description="Basic calculator for addition and multiplication",
        inputs={"operation": "string", "a": "number", "b": "number"}
    )
    
    engine.register_from_code(calculator_code, calculator_meta, persist=False)
    print("✓ Registered 'calculator' skill")
    
    # Create a compound skill that uses the calculator
    compound_formula_code = """
def compound_formula(x: float, y: float, z: float) -> dict:
    \"\"\"Calculate (x * 2) + (y * 3) + z using the calculator skill.\"\"\"
    
    # Step 1: Multiply x by 2
    step1 = call_skill('calculator', operation='multiply', a=x, b=2.0)
    result1 = step1['result']
    
    # Step 2: Multiply y by 3
    step2 = call_skill('calculator', operation='multiply', a=y, b=3.0)
    result2 = step2['result']
    
    # Step 3: Add all three values
    step3 = call_skill('calculator', operation='add', a=result1, b=result2)
    intermediate = step3['result']
    
    # Step 4: Add z
    final = call_skill('calculator', operation='add', a=intermediate, b=z)
    
    return {
        'result': final['result'],
        'formula': '(x * 2) + (y * 3) + z',
        'steps': f'{result1} + {result2} + {z} = {final["result"]}'
    }
"""
    
    compound_meta = SkillMeta(
        name="compound_formula",
        description="Calculate (x * 2) + (y * 3) + z",
        inputs={"x": "number", "y": "number", "z": "number"}
    )
    
    engine.register_from_code(compound_formula_code, compound_meta, persist=False)
    print("✓ Registered 'compound_formula' skill (uses calculator)")
    
    # Test the compound skill
    print("\nExecuting compound_formula(x=5, y=3, z=7)...")
    result = engine.run("compound_formula", {"x": 5.0, "y": 3.0, "z": 7.0})
    
    print(f"\nResult: {result['result']}")
    print(f"Formula: {result['formula']}")
    print(f"Steps: {result['steps']}")
    print(f"Expected: (5 * 2) + (3 * 3) + 7 = 10 + 9 + 7 = 26")
    print()


def demo_circular_dependency_prevention():
    """Demonstrate circular dependency detection."""
    print("=" * 60)
    print("DEMO: Circular Dependency Prevention")
    print("=" * 60)
    
    engine = SkillEngine()
    
    # Create two skills that call each other
    skill_a_code = """
def skill_a(n: int) -> dict:
    \"\"\"Skill A calls Skill B.\"\"\"
    if n <= 0:
        return {'result': 'done'}
    result = call_skill('skill_b', n=n-1)
    return {'result': f'A->{result["result"]}'}
"""
    
    skill_b_code = """
def skill_b(n: int) -> dict:
    \"\"\"Skill B calls Skill A (creating a circular dependency).\"\"\"
    if n <= 0:
        return {'result': 'done'}
    result = call_skill('skill_a', n=n-1)
    return {'result': f'B->{result["result"]}'}
"""
    
    skill_a_meta = SkillMeta(name="skill_a", description="Skill A", inputs={"n": "integer"})
    skill_b_meta = SkillMeta(name="skill_b", description="Skill B", inputs={"n": "integer"})
    
    engine.register_from_code(skill_a_code, skill_a_meta, persist=False)
    engine.register_from_code(skill_b_code, skill_b_meta, persist=False)
    
    print("✓ Registered 'skill_a' and 'skill_b' (circular dependency)")
    
    print("\nAttempting to execute skill_a(n=5)...")
    try:
        result = engine.run("skill_a", {"n": 5})
        print(f"ERROR: Should have detected circular dependency but got: {result}")
    except Exception as e:
        print(f"✓ Circular dependency detected: {str(e)}")
    print()


def demo_depth_limit():
    """Demonstrate max call depth prevention."""
    print("=" * 60)
    print("DEMO: Max Call Depth Prevention")
    print("=" * 60)
    
    engine = SkillEngine()
    
    # Create a deep chain of skills
    print("Creating a chain of 7 skills (exceeds limit of 5)...")
    for i in range(7):
        skill_name = f"level_{i}"
        next_skill = f"level_{i+1}" if i < 6 else None
        
        if next_skill:
            code = f"""
def level_{i}(value: int) -> dict:
    result = call_skill('{next_skill}', value=value+1)
    return {{'level': {i}, 'value': result['value']}}
"""
        else:
            code = f"""
def level_{i}(value: int) -> dict:
    return {{'level': {i}, 'value': value}}
"""
        
        meta = SkillMeta(name=skill_name, description=f"Level {i}", inputs={"value": "integer"})
        engine.register_from_code(code, meta, persist=False)
    
    print("✓ Registered 7 chained skills")
    
    print("\nAttempting to execute level_0(value=1)...")
    try:
        result = engine.run("level_0", {"value": 1})
        print(f"ERROR: Should have detected max depth exceeded but got: {result}")
    except Exception as e:
        print(f"✓ Max call depth exceeded: {str(e)}")
    print()


def demo_successful_chaining():
    """Demonstrate successful multi-level skill chaining."""
    print("=" * 60)
    print("DEMO: Successful Multi-Level Chaining")
    print("=" * 60)
    
    engine = SkillEngine()
    
    # Create base skills
    add_code = """
def add(a: float, b: float) -> dict:
    return {'result': a + b}
"""
    
    multiply_code = """
def multiply(a: float, b: float) -> dict:
    return {'result': a * b}
"""
    
    square_code = """
def square(x: float) -> dict:
    # Use multiply to square a number
    result = call_skill('multiply', a=x, b=x)
    return {'result': result['result']}
"""
    
    sum_of_squares_code = """
def sum_of_squares(a: float, b: float) -> dict:
    # Calculate a^2 + b^2 using square and add
    square_a = call_skill('square', x=a)
    square_b = call_skill('square', x=b)
    sum_result = call_skill('add', a=square_a['result'], b=square_b['result'])
    return {
        'result': sum_result['result'],
        'a_squared': square_a['result'],
        'b_squared': square_b['result']
    }
"""
    
    engine.register_from_code(add_code, SkillMeta(name="add", description="Add two numbers", inputs={"a": "number", "b": "number"}), persist=False)
    engine.register_from_code(multiply_code, SkillMeta(name="multiply", description="Multiply two numbers", inputs={"a": "number", "b": "number"}), persist=False)
    engine.register_from_code(square_code, SkillMeta(name="square", description="Square a number", inputs={"x": "number"}), persist=False)
    engine.register_from_code(sum_of_squares_code, SkillMeta(name="sum_of_squares", description="Sum of squares", inputs={"a": "number", "b": "number"}), persist=False)
    
    print("✓ Registered: add, multiply, square, sum_of_squares")
    print("  - square uses multiply")
    print("  - sum_of_squares uses square and add")
    
    print("\nExecuting sum_of_squares(a=3, b=4)...")
    result = engine.run("sum_of_squares", {"a": 3.0, "b": 4.0})
    
    print(f"\nResult: {result['result']}")
    print(f"3² = {result['a_squared']}")
    print(f"4² = {result['b_squared']}")
    print(f"3² + 4² = {result['result']}")
    print(f"Expected: 9 + 16 = 25")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SKILL COMPOSITION DEMONSTRATION")
    print("Skills can now call other skills using call_skill()")
    print("=" * 60 + "\n")
    
    demo_basic_composition()
    demo_successful_chaining()
    demo_circular_dependency_prevention()
    demo_depth_limit()
    
    print("=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)

