with profile_defaults(name, description) as (
  values
    ('Less than 10', 'Default safety profile for children younger than 10.'),
    ('10-13', 'Default safety profile for learners aged 10 through 13.'),
    ('13-15', 'Default safety profile for learners aged 13 through 15.'),
    ('15-17', 'Default safety profile for learners aged 15 through 17.')
)
insert into public.safety_profile_definitions (name, description)
select name, description from profile_defaults
on conflict (name) do nothing;

with profile_defaults(name, age_band, reading_level, prompt_content, threshold) as (
  values
    ('Less than 10', 'Less than 10', 'grade 4', 'The learner is younger than 10 and reads at approximately grade 4. Use short, warm, concrete sentences. Keep answers under 120 words. Avoid profanity, insults, explicit sexual content, graphic violence, mature themes, and instructions for wrongdoing. Give factual, non-graphic, age-appropriate explanations and encourage a trusted adult when appropriate.', 0.05::numeric),
    ('10-13', '10-13', 'grade 6', 'The learner is 10 to 13 years old and reads at approximately grade 6. Be clear, encouraging, and practical. Keep answers under 150 words. Discuss health and safety topics factually but non-graphically. Avoid explicit sexual content, graphic violence, mature wrongdoing details, profanity, and insults.', 0.07::numeric),
    ('13-15', '13-15', 'grade 8', 'The learner is 13 to 15 years old and reads at approximately grade 8. Be respectful, direct, and educational. Keep answers under 180 words. Give age-appropriate factual context for health, relationships, history, and safety topics without explicit sexual content, graphic violence, harmful instructions, profanity, or harassment.', 0.09::numeric),
    ('15-17', '15-17', 'grade 10', 'The learner is 15 to 17 years old and reads at approximately grade 10. Be respectful, accurate, and constructive. Keep answers under 220 words. Offer factual, age-appropriate context for health, relationships, history, and safety topics while avoiding explicit sexual content involving minors, graphic violence, harmful instructions, harassment, and profanity.', 0.11::numeric)
), threshold_profiles as (
  select
    name,
    age_band,
    reading_level,
    prompt_content,
    jsonb_build_object(
      'harassment', threshold + 0.05,
      'harassment/threatening', threshold / 2,
      'hate', threshold,
      'hate/threatening', threshold / 2,
      'illicit', threshold,
      'illicit/violent', threshold / 3,
      'self-harm', threshold / 2,
      'self-harm/intent', threshold / 3,
      'self-harm/instructions', 0.01,
      'sexual', threshold,
      'sexual/minors', 0.01,
      'violence', threshold + 0.03,
      'violence/graphic', threshold / 2
    ) as input_thresholds
  from profile_defaults
), versions as (
  select
    name,
    age_band,
    reading_level,
    prompt_content,
    input_thresholds,
    (
      select jsonb_object_agg(category, to_jsonb(greatest((maximum #>> '{}')::numeric - 0.02, 0.01)))
      from jsonb_each(input_thresholds) as score(category, maximum)
    ) as output_thresholds
  from threshold_profiles
)
insert into public.safety_profile_versions (safety_profile_id, version, status, age_band, reading_level, prompt_content, input_thresholds, output_thresholds)
select definitions.id, 1, 'active', versions.age_band, versions.reading_level, versions.prompt_content, versions.input_thresholds, versions.output_thresholds
from versions
join public.safety_profile_definitions definitions on definitions.name = versions.name
where not exists (
  select 1 from public.safety_profile_versions existing
  where existing.safety_profile_id = definitions.id and existing.version = 1
);
