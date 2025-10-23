"""Unit tests for skill composition and inter-skill calling."""

import pytest
from backend.skill_engine import (
    SkillEngine,
    SkillContext,
    SkillMeta,
    SkillNotFound,
    SkillRuntimeError,
    SkillRegistrationError
)


class TestSkillContext:
    """Test the SkillContext class for managing skill calls."""
    
    def test_context_creation(self):
        """Test that SkillContext can be created."""
        engine = SkillEngine()
        context = SkillContext(engine)
        
        assert context._engine is engine
        assert context._call_stack == []
        assert context._max_call_depth == 5
    
    def test_context_with_custom_depth(self):
        """Test creating context with custom max depth."""
        engine = SkillEngine()
        context = SkillContext(engine, max_call_depth=10)
        
        assert context._max_call_depth == 10
    
    def test_context_with_call_stack(self):
        """Test creating context with existing call stack."""
        engine = SkillEngine()
        call_stack = ["skill1", "skill2"]
        context = SkillContext(engine, call_stack=call_stack)
        
        assert context._call_stack == call_stack


class TestBasicSkillCalling:
    """Test basic skill calling another skill."""
    
    def test_skill_calls_another_skill(self):
        """Test that one skill can call another skill."""
        engine = SkillEngine()
        
        # Register a simple calculator skill
        calculator_code = """
def calculator(operation: str, a: float, b: float) -> dict:
    \"\"\"Basic calculator skill.\"\"\"
    if operation == 'add':
        return {'result': a + b}
    elif operation == 'multiply':
        return {'result': a * b}
    else:
        return {'error': 'Unknown operation'}
"""
        calculator_meta = SkillMeta(
            name="calculator",
            description="Basic calculator",
            inputs={"operation": "string", "a": "number", "b": "number"}
        )
        engine.register_from_code(calculator_code, calculator_meta, persist=False)
        
        # Register a skill that uses the calculator
        double_and_add_code = """
def double_and_add(x: float, y: float) -> dict:
    \"\"\"Double x, then add y using the calculator skill.\"\"\"
    # Double x
    doubled = call_skill('calculator', operation='multiply', a=x, b=2.0)
    doubled_value = doubled['result']
    
    # Add y
    result = call_skill('calculator', operation='add', a=doubled_value, b=y)
    
    return {'result': result['result'], 'steps': ['doubled', 'added']}
"""
        double_meta = SkillMeta(
            name="double_and_add",
            description="Double x then add y",
            inputs={"x": "number", "y": "number"}
        )
        engine.register_from_code(double_and_add_code, double_meta, persist=False)
        
        # Execute the composite skill
        result = engine.run("double_and_add", {"x": 5.0, "y": 3.0})
        
        # 5 * 2 = 10, 10 + 3 = 13
        assert result['result'] == 13.0
        assert result['steps'] == ['doubled', 'added']
    
    def test_skill_calls_multiple_different_skills(self):
        """Test a skill calling multiple different skills."""
        engine = SkillEngine()
        
        # Register skill 1: add two numbers
        add_code = """
def add_numbers(a: float, b: float) -> dict:
    return {'result': a + b}
"""
        add_meta = SkillMeta(name="add_numbers", description="Add two numbers", inputs={"a": "number", "b": "number"})
        engine.register_from_code(add_code, add_meta, persist=False)
        
        # Register skill 2: multiply two numbers
        multiply_code = """
def multiply_numbers(a: float, b: float) -> dict:
    return {'result': a * b}
"""
        multiply_meta = SkillMeta(name="multiply_numbers", description="Multiply two numbers", inputs={"a": "number", "b": "number"})
        engine.register_from_code(multiply_code, multiply_meta, persist=False)
        
        # Register composite skill: (a + b) * c
        composite_code = """
def sum_then_multiply(a: float, b: float, c: float) -> dict:
    # First add a and b
    sum_result = call_skill('add_numbers', a=a, b=b)
    sum_value = sum_result['result']
    
    # Then multiply by c
    product_result = call_skill('multiply_numbers', a=sum_value, b=c)
    
    return {'result': product_result['result']}
"""
        composite_meta = SkillMeta(
            name="sum_then_multiply",
            description="Add a and b, then multiply by c",
            inputs={"a": "number", "b": "number", "c": "number"}
        )
        engine.register_from_code(composite_code, composite_meta, persist=False)
        
        # Execute: (2 + 3) * 4 = 20
        result = engine.run("sum_then_multiply", {"a": 2.0, "b": 3.0, "c": 4.0})
        assert result['result'] == 20.0


class TestCircularDependencyPrevention:
    """Test circular dependency detection."""
    
    def test_direct_circular_dependency(self):
        """Test that direct circular dependency is detected."""
        engine = SkillEngine()
        
        # Register a skill that calls itself
        recursive_code = """
def recursive_skill(n: int) -> dict:
    if n <= 0:
        return {'result': 0}
    # This will cause circular dependency
    result = call_skill('recursive_skill', n=n-1)
    return {'result': n + result['result']}
"""
        recursive_meta = SkillMeta(name="recursive_skill", description="Recursive skill", inputs={"n": "integer"})
        engine.register_from_code(recursive_code, recursive_meta, persist=False)
        
        # Attempting to run should raise SkillRuntimeError about circular dependency
        with pytest.raises(SkillRuntimeError) as exc_info:
            engine.run("recursive_skill", {"n": 5})
        
        assert "Circular dependency detected" in str(exc_info.value)
    
    def test_indirect_circular_dependency(self):
        """Test that indirect circular dependency (A -> B -> A) is detected."""
        engine = SkillEngine()
        
        # Skill A calls B
        skill_a_code = """
def skill_a(x: int) -> dict:
    result = call_skill('skill_b', x=x)
    return {'result': result['result'] + 1}
"""
        skill_a_meta = SkillMeta(name="skill_a", description="Skill A", inputs={"x": "integer"})
        engine.register_from_code(skill_a_code, skill_a_meta, persist=False)
        
        # Skill B calls A (creating circular dependency)
        skill_b_code = """
def skill_b(x: int) -> dict:
    if x > 10:
        return {'result': x}
    result = call_skill('skill_a', x=x+1)
    return {'result': result['result'] + 1}
"""
        skill_b_meta = SkillMeta(name="skill_b", description="Skill B", inputs={"x": "integer"})
        engine.register_from_code(skill_b_code, skill_b_meta, persist=False)
        
        # This should detect the circular dependency
        with pytest.raises(SkillRuntimeError) as exc_info:
            engine.run("skill_a", {"x": 1})
        
        assert "Circular dependency detected" in str(exc_info.value)


class TestMaxDepthPrevention:
    """Test max call depth prevention."""
    
    def test_max_depth_exceeded(self):
        """Test that excessive call depth is prevented."""
        engine = SkillEngine()
        
        # Create a chain of skills: A -> B -> C -> D -> E -> F -> G (7 levels of calls)
        # Max depth is 5, so when skill_A calls B, B calls C, C calls D, D calls E, E calls F, F tries to call G
        # The stack will be [B, C, D, E, F] (length 5) when G is attempted, which should fail
        for i in range(7):
            skill_name = f"skill_{chr(65+i)}"  # A, B, C, D, E, F, G
            next_skill = f"skill_{chr(66+i)}" if i < 6 else None
            
            if next_skill:
                code = f"""
def skill_{chr(65+i)}(x: int) -> dict:
    result = call_skill('{next_skill}', x=x+1)
    return {{'result': result['result'] + 1}}
"""
            else:
                code = f"""
def skill_{chr(65+i)}(x: int) -> dict:
    return {{'result': x}}
"""
            
            meta = SkillMeta(name=skill_name, description=f"Skill {chr(65+i)}", inputs={"x": "integer"})
            engine.register_from_code(code, meta, persist=False)
        
        # Default max depth is 5, so this chain should fail
        with pytest.raises(SkillRuntimeError) as exc_info:
            engine.run("skill_A", {"x": 1})
        
        assert "Max call depth" in str(exc_info.value) or "exceeded" in str(exc_info.value)
    
    def test_max_depth_not_exceeded_within_limit(self):
        """Test that calls within the depth limit work fine."""
        engine = SkillEngine()
        
        # Create a chain of 4 skills (within limit of 5)
        for i in range(4):
            skill_name = f"skill_{i}"
            next_skill = f"skill_{i+1}" if i < 3 else None
            
            if next_skill:
                code = f"""
def skill_{i}(x: int) -> dict:
    result = call_skill('{next_skill}', x=x+1)
    return {{'result': result['result'] + 1}}
"""
            else:
                code = f"""
def skill_{i}(x: int) -> dict:
    return {{'result': x}}
"""
            
            meta = SkillMeta(name=skill_name, description=f"Skill {i}", inputs={"x": "integer"})
            engine.register_from_code(code, meta, persist=False)
        
        # This should succeed (4 levels is within limit)
        result = engine.run("skill_0", {"x": 10})
        # Each level adds 1, starting from 10+1+1+1 = 13, then +1 for each return = 16
        assert result['result'] == 16


class TestErrorPropagation:
    """Test that errors propagate correctly through skill calls."""
    
    def test_error_from_called_skill_propagates(self):
        """Test that errors from called skills propagate to caller."""
        engine = SkillEngine()
        
        # Register a skill that raises an error
        failing_code = """
def failing_skill(should_fail: bool) -> dict:
    if should_fail:
        raise ValueError("This skill failed!")
    return {'result': 'success'}
"""
        failing_meta = SkillMeta(name="failing_skill", description="Skill that can fail", inputs={"should_fail": "boolean"})
        engine.register_from_code(failing_code, failing_meta, persist=False)
        
        # Register a skill that calls the failing skill
        caller_code = """
def caller_skill(trigger_error: bool) -> dict:
    result = call_skill('failing_skill', should_fail=trigger_error)
    return {'result': result['result']}
"""
        caller_meta = SkillMeta(name="caller_skill", description="Calls failing skill", inputs={"trigger_error": "boolean"})
        engine.register_from_code(caller_code, caller_meta, persist=False)
        
        # Should fail when we trigger the error
        with pytest.raises(SkillRuntimeError):
            engine.run("caller_skill", {"trigger_error": True})
        
        # Should succeed when we don't trigger the error
        result = engine.run("caller_skill", {"trigger_error": False})
        assert result['result'] == 'success'
    
    def test_skill_not_found_error_propagates(self):
        """Test that SkillNotFound error propagates when calling non-existent skill."""
        engine = SkillEngine()
        
        # Register a skill that tries to call a non-existent skill
        caller_code = """
def caller_skill() -> dict:
    result = call_skill('nonexistent_skill', x=42)
    return {'result': result}
"""
        caller_meta = SkillMeta(name="caller_skill", description="Calls non-existent skill", inputs={})
        engine.register_from_code(caller_code, caller_meta, persist=False)
        
        # Should raise SkillRuntimeError (which wraps the SkillNotFound)
        with pytest.raises(SkillRuntimeError) as exc_info:
            engine.run("caller_skill", {})
        
        # Check that the error message mentions the nonexistent skill
        assert "nonexistent_skill" in str(exc_info.value)


class TestBackwardCompatibility:
    """Test that skills without call_skill still work."""
    
    def test_skill_without_call_skill_works(self):
        """Test that traditional skills without inter-skill calling still work."""
        engine = SkillEngine()
        
        # Register a simple skill that doesn't call other skills
        simple_code = """
def simple_skill(x: int, y: int) -> dict:
    return {'result': x + y}
"""
        simple_meta = SkillMeta(name="simple_skill", description="Simple skill", inputs={"x": "integer", "y": "integer"})
        engine.register_from_code(simple_code, simple_meta, persist=False)
        
        # Should work normally
        result = engine.run("simple_skill", {"x": 10, "y": 5})
        assert result['result'] == 15


class TestComplexComposition:
    """Test complex skill composition scenarios."""
    
    def test_parallel_skill_calls(self):
        """Test a skill that calls multiple skills and combines results."""
        engine = SkillEngine()
        
        # Register base skills
        double_code = """
def double(x: float) -> dict:
    return {'result': x * 2}
"""
        triple_code = """
def triple(x: float) -> dict:
    return {'result': x * 3}
"""
        double_meta = SkillMeta(name="double", description="Double a number", inputs={"x": "number"})
        triple_meta = SkillMeta(name="triple", description="Triple a number", inputs={"x": "number"})
        
        engine.register_from_code(double_code, double_meta, persist=False)
        engine.register_from_code(triple_code, triple_meta, persist=False)
        
        # Register composite skill that uses both
        composite_code = """
def double_and_triple(x: float) -> dict:
    doubled = call_skill('double', x=x)
    tripled = call_skill('triple', x=x)
    return {
        'doubled': doubled['result'],
        'tripled': tripled['result'],
        'sum': doubled['result'] + tripled['result']
    }
"""
        composite_meta = SkillMeta(
            name="double_and_triple",
            description="Double and triple a number",
            inputs={"x": "number"}
        )
        engine.register_from_code(composite_code, composite_meta, persist=False)
        
        # Execute
        result = engine.run("double_and_triple", {"x": 5.0})
        assert result['doubled'] == 10.0
        assert result['tripled'] == 15.0
        assert result['sum'] == 25.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

