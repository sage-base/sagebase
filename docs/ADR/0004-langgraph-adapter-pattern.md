# ADR 001: LangGraph Adapter Pattern for Party Scraping Workflow

## Status

Accepted

## Context

In implementing Issue #613 (PBI-006 LangGraph Agent統合とワークフロー実装), we needed to integrate LangGraph's StateGraph framework for hierarchical party scraping workflows while maintaining Clean Architecture principles.

### The Challenge

LangGraph requires specific type signatures for its nodes and state:
- Nodes must accept and return `LangGraphPartyScrapingState` (TypedDict)
- State management is handled by LangGraph's StateGraph
- Conditional edges require specific return value formats

However, Clean Architecture requires:
- Domain entities should be framework-independent
- Business logic should not depend on external frameworks
- Dependencies should only point inward (Domain ← Application ← Infrastructure)

### The Dilemma

Two competing constraints:
1. **Framework Integration**: LangGraph nodes need framework-specific types (`LangGraphPartyScrapingState`)
2. **Domain Independence**: Our domain entity (`PartyScrapingState`) must remain framework-independent

## Decision

We accept using LangGraph-specific types in our infrastructure layer node signatures, but implement an **Adapter Pattern** to maintain domain independence:

### Solution Components

1. **Domain Entity** (`PartyScrapingState`):
   - Pure Python dataclass
   - Framework-independent
   - Contains all business logic
   - Located in `src/domain/entities/`

2. **LangGraph State** (`LangGraphPartyScrapingState`):
   - TypedDict for LangGraph compatibility
   - Located in `src/infrastructure/external/langgraph_state_adapter.py`
   - Used only in infrastructure layer

3. **Adapters**:
   - `domain_to_langgraph_state()`: Converts domain → framework
   - `langgraph_to_domain_state()`: Converts framework → domain
   - Located in `src/infrastructure/external/langgraph_state_adapter.py`

4. **Node Signatures**:
   - Nodes accept `LangGraphPartyScrapingStateOptional`
   - Nodes return `LangGraphPartyScrapingStateOptional`
   - This is **acceptable** because nodes are in infrastructure layer

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Infrastructure Layer                                         │
│                                                              │
│  LangGraph StateGraph                                        │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐   │
│  │ Node 1     │─────>│ Node 2     │─────>│ Node 3     │   │
│  └────────────┘      └────────────┘      └────────────┘   │
│       │                    │                    │           │
│       │ (LangGraphState)   │                    │           │
│       ▼                    ▼                    ▼           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Adapter: domain_to_langgraph_state()        │  │
│  │                     ▲       │                         │  │
│  │  langgraph_to_domain_state()                         │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────────│────────────▲────────────────┘
                                 │            │
┌────────────────────────────────▼────────────┴────────────────┐
│ Domain Layer                                                  │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ PartyScrapingState (Framework-Independent)          │   │
│  │ - current_url                                        │   │
│  │ - visited_urls: set[str]                            │   │
│  │ - pending_urls: list[tuple[str, int]]              │   │
│  │ - extracted_members: list[dict]                     │   │
│  │ - Business methods (is_complete, add_url, etc.)    │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

1. **Domain Independence Maintained**: `PartyScrapingState` has no LangGraph dependencies
2. **Framework Integration Works**: LangGraph nodes function correctly
3. **Testability**: Domain logic can be tested without LangGraph
4. **Future Migration Path**: If we switch frameworks, only adapter layer changes
5. **Type Safety**: Both domain and infrastructure layers maintain type safety

### Negative (Acceptable Trade-offs)

1. **Framework Types in Infrastructure**: Node signatures use `LangGraphPartyScrapingState`
   - **Why Acceptable**: Nodes are in infrastructure layer, which is allowed to depend on frameworks
   - **Boundary**: Framework types never leak into domain or application layers

2. **Adapter Overhead**: Conversion between domain and framework states
   - **Why Acceptable**: Conversion is simple dictionary manipulation, minimal cost
   - **Benefit**: Provides clear integration boundary

3. **Type Complexity**: Two state representations to maintain
   - **Why Acceptable**: Clear separation of concerns, documented in adapter module
   - **Mitigation**: Comprehensive adapter tests ensure consistency

### Technical Debt

This is **NOT** considered technical debt because:
- It follows Clean Architecture adapter pattern correctly
- Infrastructure layer is allowed to use framework-specific types
- Domain layer remains pure and framework-independent
- Clear migration path if framework changes

### Constraints

1. **Never expose LangGraph types to**:
   - Domain layer entities or services
   - Application layer use cases
   - Domain service interfaces

2. **Adapter module responsibilities**:
   - Maintain both type definitions
   - Provide bidirectional conversion
   - Include comprehensive conversion tests

3. **Node implementations**:
   - Accept LangGraph state (infrastructure layer)
   - Call domain services (framework-independent)
   - Return LangGraph state

## Implementation

### Files Affected

- `src/domain/entities/party_scraping_state.py` (domain entity)
- `src/infrastructure/external/langgraph_state_adapter.py` (adapter)
- `src/infrastructure/external/langgraph_nodes/*.py` (node implementations)
- `src/infrastructure/external/langgraph_party_scraping_agent_with_classification.py` (agent)

### Code Example

```python
# Domain Layer (Framework-Independent)
@dataclass
class PartyScrapingState:
    current_url: str
    visited_urls: set[str] = field(default_factory=set)
    # ... business methods

# Infrastructure Layer (Framework-Specific)
class LangGraphPartyScrapingState(TypedDict, total=False):
    current_url: str
    visited_urls: set[str]
    # ... LangGraph-compatible types

# Adapter (Infrastructure Layer)
def domain_to_langgraph_state(domain: PartyScrapingState) -> LangGraphPartyScrapingState:
    return {
        "current_url": domain.current_url,
        "visited_urls": domain.visited_urls,
        # ... field mapping
    }

# Node (Infrastructure Layer - LangGraph types OK here)
def create_node(service: IDomainService) -> Callable:
    async def node(state: LangGraphPartyScrapingState) -> LangGraphPartyScrapingState:
        # Use domain service (framework-independent)
        result = await service.do_work(state["current_url"])
        return {"result": result}
    return node
```

## Alternatives Considered

### Alternative 1: Make PartyScrapingState Inherit from TypedDict
**Rejected**: Would couple domain entity to LangGraph framework

### Alternative 2: Use LangGraph Types Everywhere
**Rejected**: Violates Clean Architecture, domain would depend on framework

### Alternative 3: Create Generic State Wrapper
**Rejected**: Adds unnecessary complexity, adapter pattern is simpler and clearer

## References

- Issue #613: [PBI-006] LangGraph Agent統合とワークフロー実装
- Clean Architecture Review: `tmp/clean_architecture_review_*.md`
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Clean Architecture Book: Robert C. Martin

## Review and Updates

- **Created**: 2025-01-21
- **Status**: Accepted
- **Next Review**: When considering framework migration or major architectural changes

## Notes

This ADR documents a deliberate architectural decision that was initially flagged as CRITICAL-3 during clean architecture review. After analysis, the team determined this pattern is:
- Architecturally sound
- Follows adapter pattern correctly
- Does not violate dependency inversion principle
- Should be documented rather than changed

The infrastructure layer's use of framework-specific types is **by design**, not a violation.
