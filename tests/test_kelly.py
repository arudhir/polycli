"""Tests for Kelly Criterion calculator."""

from decimal import Decimal

import pytest

from polycli.position.kelly import KellyCalculator, KellyFraction


class TestKellyCalculator:
    """Tests for Kelly calculations."""

    def test_positive_edge(self) -> None:
        """Test calculation with positive edge."""
        calc = KellyCalculator(Decimal("10000"))
        result = calc.calculate(
            win_probability=Decimal("0.6"),
            market_price=Decimal("0.5"),
        )

        assert result.is_positive_ev
        assert result.edge == Decimal("0.1")
        assert result.recommended_bet_size > 0

    def test_negative_edge(self) -> None:
        """Test calculation with negative edge."""
        calc = KellyCalculator(Decimal("10000"))
        result = calc.calculate(
            win_probability=Decimal("0.4"),
            market_price=Decimal("0.5"),
        )

        assert not result.is_positive_ev
        assert result.edge == Decimal("-0.1")
        assert result.recommended_bet_size == 0

    def test_kelly_fraction(self) -> None:
        """Test different Kelly fractions."""
        calc = KellyCalculator(Decimal("10000"))

        full = calc.calculate(
            win_probability=Decimal("0.6"),
            market_price=Decimal("0.4"),
            kelly_fraction=KellyFraction.FULL,
        )

        quarter = calc.calculate(
            win_probability=Decimal("0.6"),
            market_price=Decimal("0.4"),
            kelly_fraction=KellyFraction.QUARTER,
        )

        assert quarter.recommended_fraction < full.recommended_fraction
        assert quarter.recommended_bet_size < full.recommended_bet_size

    def test_invalid_probability(self) -> None:
        """Test invalid probability raises error."""
        calc = KellyCalculator(Decimal("10000"))

        with pytest.raises(ValueError):
            calc.calculate(
                win_probability=Decimal("1.5"),
                market_price=Decimal("0.5"),
            )

    def test_max_bet_cap(self) -> None:
        """Test max bet cap is enforced."""
        calc = KellyCalculator(
            Decimal("10000"),
            max_bet_fraction=Decimal("0.05"),
        )

        result = calc.calculate(
            win_probability=Decimal("0.9"),
            market_price=Decimal("0.3"),
        )

        # Even with huge edge, capped at 5%
        assert result.recommended_fraction <= Decimal("0.05")
