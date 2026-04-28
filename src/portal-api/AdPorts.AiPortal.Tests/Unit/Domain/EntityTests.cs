using AdPorts.AiPortal.Domain.Entities;
using FluentAssertions;
using Xunit;

namespace AdPorts.AiPortal.Tests.Unit.Domain;

public class ProjectTests
{
    [Fact]
    public void Create_ValidInputs_SetsProperties()
    {
        var project = Project.Create("my-project", "My Project", "JUL", "desc", Guid.NewGuid());
        project.Slug.Should().Be("my-project");
        project.DisplayName.Should().Be("My Project");
        project.Status.Should().Be("active");
    }

    [Fact]
    public void Create_SlugUpperCase_NormalisedToLower()
    {
        var project = Project.Create("My-Project", "My Project", null, null, null);
        project.Slug.Should().Be("my-project");
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public void Create_EmptySlug_Throws(string slug)
    {
        var act = () => Project.Create(slug, "Name", null, null, null);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void Update_ChangesDisplayNameAndProgram()
    {
        var project = Project.Create("proj", "Old Name", null, null, null);
        project.Update("New Name", "updated desc", "PCS");
        project.DisplayName.Should().Be("New Name");
        project.Program.Should().Be("PCS");
    }
}

public class TeamMemberTests
{
    [Theory]
    [InlineData("invalid-role")]
    [InlineData("")]
    public void Add_InvalidRole_Throws(string role)
    {
        var act = () => TeamMember.Add(Guid.NewGuid(), Guid.NewGuid(), role);
        act.Should().Throw<ArgumentException>();
    }

    [Fact]
    public void Add_ValidRole_Succeeds()
    {
        var member = TeamMember.Add(Guid.NewGuid(), Guid.NewGuid(), "architect");
        member.Role.Should().Be("architect");
    }
}

public class ApprovalTests
{
    [Fact]
    public void Create_ValidDecision_Succeeds()
    {
        var approval = Approval.Create(Guid.NewGuid(), Guid.NewGuid(), "approved", "LGTM", "{}", null);
        approval.Decision.Should().Be("approved");
    }

    [Fact]
    public void Create_InvalidDecision_Throws()
    {
        var act = () => Approval.Create(Guid.NewGuid(), Guid.NewGuid(), "maybe", null, "{}", null);
        act.Should().Throw<ArgumentException>();
    }
}
